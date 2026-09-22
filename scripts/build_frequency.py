"""Heuristic frequency weighting for Rime dictionary entries.

Assigns weights based on source authority, word length, cross-source overlap,
and optional corpus frequency data.
"""

import math
import re
import unicodedata
from pathlib import Path

SOURCE_WEIGHTS = {
    "moe": 1000,  # L1: 教育部辭典
    "moe_tl": 700,  # L1b: 教育部辭典全羅 TL 輸出候選
    "moe_poj": 650,  # L1b: 教育部辭典全羅 POJ 輸出候選
    "itaigi": 800,  # L2: iTaigi (群眾驗證)
    "taihoa": 500,  # L3: 台華線頂
    "maryknoll": 300,  # L4: Maryknoll 台英辭典
    "embree": 300,  # L4: Embree 台英辭典
    "kamjitian": 250,  # L4: 甘字典
    "taijit": 200,  # L5: 台日大辭典
    "pehoe": 200,  # L5: 台灣白話基礎語句
    "sitbut": 200,  # L5: 台灣實物名彙
}
DEFAULT_WEIGHT = 100


def assign_source_weight(source: str) -> int:
    """Return base frequency weight for a given data source.

    Args:
        source: Source identifier (moe, itaigi, taihoa, taijit)

    Returns:
        Integer weight (higher = more frequent/authoritative)
    """
    return SOURCE_WEIGHTS.get(source, DEFAULT_WEIGHT)


def _count_cjk_chars(text: str) -> int:
    """Count CJK ideograph characters in text."""
    count = 0
    for ch in text:
        if unicodedata.category(ch).startswith("Lo"):
            count += 1
    return count


def word_length_modifier(hanlo: str) -> float:
    """Return weight multiplier based on word length.

    Args:
        hanlo: Han-Lo mixed text

    Returns:
        Multiplier: 0.8 (1 char), 1.2 (2-3 chars), 0.6 (4+ chars), 1.0 (pure romanization)
    """
    length = _count_cjk_chars(hanlo)
    if length == 0:
        return 1.0
    if length == 1:
        return 0.8
    if length <= 3:
        return 1.2
    return 0.6


def load_corpus_frequencies(freq_path: Path) -> dict[str, int]:
    """Load corpus frequency table from TSV file.

    Args:
        freq_path: Path to TSV with word\\tcount format

    Returns:
        Dict mapping words to frequency counts
    """
    if not freq_path.exists():
        return {}
    result: dict[str, int] = {}
    with open(freq_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                try:
                    result[parts[0]] = int(parts[1])
                except ValueError:
                    continue
    return result


def compute_weights(
    entries: list[dict],
    corpus_freq: dict[str, int] | None = None,
) -> list[dict]:
    """Compute final frequency weights for dictionary entries.

    Combines source authority, word length modifier, cross-source overlap bonus,
    and optional corpus frequency boost.

    Args:
        entries: List of dicts with hanlo, rime_key, source fields
        corpus_freq: Optional dict mapping kip_input to corpus occurrence counts

    Returns:
        Deduplicated list with computed 'weight' field (int)
    """
    if corpus_freq is None:
        corpus_freq = {}

    # Count how many sources each (hanlo, rime_key) pair appears in
    key_sources: dict[tuple[str, str], set[str]] = {}
    for entry in entries:
        key = (entry["hanlo"], entry["rime_key"])
        key_sources.setdefault(key, set()).add(entry["source"])

    # Group entries by key, keep best source
    best_entries: dict[tuple[str, str], dict] = {}
    for entry in entries:
        key = (entry["hanlo"], entry["rime_key"])
        source_weight = assign_source_weight(entry["source"])
        existing = best_entries.get(key)
        if existing is None or source_weight > assign_source_weight(existing["source"]):
            best_entries[key] = entry.copy()

    # Compute final weights
    result = []
    for key, entry in best_entries.items():
        base = assign_source_weight(entry["source"])
        length_mod = word_length_modifier(entry["hanlo"])
        overlap_bonus = 1.1 ** (len(key_sources[key]) - 1)

        # Corpus frequency boost: log-scale boost if word appears in corpus
        corpus_boost = 1.0
        kip = entry.get("kip_input", "")
        if kip and kip in corpus_freq:
            corpus_boost = 1.0 + math.log10(1 + corpus_freq[kip]) * 0.2

        entry["weight"] = int(base * length_mod * overlap_bonus * corpus_boost)
        result.append(entry)

    return result


# rime_key syllable tokens: split on spaces and hyphen runs (covers "--" light tone)
_SYLLABLE_SPLIT_RE = re.compile(r"[ \-]+")



def enforce_long_word_invariant(entries: list[dict], k: float = 1.2) -> tuple[list[dict], int]:
    """Enforce the long-word-first weight invariant (PLAN section 9-1A).

    For every multi-syllable entry W, raise weight(W) to at least
    ceil(k * sum(weights of the strongest single-syllable entries with
    the same readings)). This guarantees the Rime sentence composer can
    never prefer fragmenting a dictionary word into single characters.

    Single-syllable entries are never modified; multi-syllable entries
    whose syllables have no standalone competitors are left unchanged.
    Idempotent: a second run raises nothing.

    Args:
        entries: Output of compute_weights (each dict has rime_key and weight).
            Dicts are modified in place and the same list is returned.
        k: Safety margin over the fragmented sum (default 1.2).

    Returns:
        (entries, number of entries whose weight was raised)
    """
    syllable_best: dict[str, int] = {}
    for entry in entries:
        tokens = [t for t in _SYLLABLE_SPLIT_RE.split(entry["rime_key"]) if t]
        if len(tokens) == 1:
            weight = entry["weight"]
            if weight > syllable_best.get(tokens[0], 0):
                syllable_best[tokens[0]] = weight

    raised = 0
    for entry in entries:
        tokens = [t for t in _SYLLABLE_SPLIT_RE.split(entry["rime_key"]) if t]
        if len(tokens) < 2:
            continue
        fragmented_sum = sum(syllable_best.get(token, 0) for token in tokens)
        if fragmented_sum <= 0:
            continue
        threshold = math.ceil(k * fragmented_sum)
        if entry["weight"] < threshold:
            entry["weight"] = threshold
            raised += 1

    return entries, raised


def enforce_dict_file_invariant(dict_path: Path, k: float = 1.2) -> int:
    """Enforce the long-word invariant on an assembled Rime dict.yaml.

    Reads the dict file, applies enforce_long_word_invariant to its data
    rows, and rewrites only the weights that changed. Use as the final
    pass after all append steps (phrases, light tone) so the whole
    assembled dictionary satisfies the invariant.

    Args:
        dict_path: Path to a dict.yaml with a --- header block.
        k: Safety margin over the fragmented sum (default 1.2).

    Returns:
        Number of rows whose weight was raised.
    """
    lines = dict_path.read_text(encoding="utf-8").splitlines()

    # Locate data rows (after the closing "..." of the YAML header)
    data_start = 0
    for i, line in enumerate(lines):
        if line == "...":
            data_start = i + 1
            break

    entries: list[dict] = []
    row_index: list[int] = []  # entries[i] lives at lines[row_index[i]]
    for i in range(data_start, len(lines)):
        parts = lines[i].split("\t")
        if len(parts) < 3 or not parts[2].strip().isdigit():
            continue
        entries.append(
            {"hanlo": parts[0], "rime_key": parts[1], "weight": int(parts[2])}
        )
        row_index.append(i)

    _, raised = enforce_long_word_invariant(entries, k=k)

    for entry, line_no in zip(entries, row_index, strict=True):
        parts = lines[line_no].split("\t")
        parts[2] = str(entry["weight"])
        lines[line_no] = "\t".join(parts)

    dict_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return raised
