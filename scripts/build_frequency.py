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
    "moe_variant": 550,  # ChhoeTaigi rows self-declined as variants (本辭典使用「X」來表示)
}
DEFAULT_WEIGHT = 100
CORPUS_BOOST_COEFF = 0.3


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


def load_identity_frequencies(freq_path: Path) -> dict[tuple[str, str], int]:
    """Load per-identity corpus counts from TSV.

    Args:
        freq_path: TSV with hanlo\\tkip_input\\tcount rows

    Returns:
        Dict mapping (hanlo, kip_input) → count; malformed rows skipped
    """
    if not freq_path.exists():
        return {}
    result: dict[tuple[str, str], int] = {}
    with open(freq_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            try:
                result[(parts[0], parts[1])] = int(parts[2])
            except ValueError:
                continue
    return result


def compute_weights(
    entries: list[dict],
    corpus_freq: dict[str, int] | None = None,
    identity_freq: dict[tuple[str, str], int] | None = None,
) -> list[dict]:
    """Compute final frequency weights for dictionary entries.

    Combines source authority, word length modifier, cross-source overlap bonus,
    and corpus frequency boost.

    Args:
        entries: List of dicts with hanlo, rime_key, source fields
        corpus_freq: Optional dict mapping kip_input to corpus occurrence counts
            (TL-only: conflates same-code homophones)
        identity_freq: Optional dict mapping (hanlo, kip_input) to corpus
            occurrence counts from aligned parallel corpora. When any entry of
            a code has identity data, per-entry identity counts are the only
            corpus evidence used for that code, so same-code homophones
            (人/膿) rank by their own observed usage.

    Returns:
        Deduplicated list with computed 'weight' field (int)
    """
    if corpus_freq is None:
        corpus_freq = {}
    identity_freq = identity_freq or {}
    # Codes covered by identity evidence: TL-only counts would attribute
    # homophone mass to unseen words, so they stop applying per code.
    # Identity kips are hyphenated; canonicalize to the space-separated
    # rime-key form before comparing.
    codes_with_identity: set[str] = set()
    for _han, kip in identity_freq:
        codes_with_identity.add(" ".join(kip.replace("-", " ").split()))

    def dedup_key(entry: dict) -> tuple[str, str, bool]:
        # Whitespace runs are typography, not identity — but the double
        # space a light-tone `--` marker produces IS part of the reading
        # (kì--tit vs kì-tit), so the marker keeps its own identity row.
        canonical = " ".join(entry["rime_key"].split())
        lighttone = "--" in entry.get("kip_input", "")
        return (entry["hanlo"], canonical, lighttone)

    # Count how many sources each word identity appears in
    key_sources: dict[tuple[str, str, bool], set[str]] = {}
    for entry in entries:
        key_sources.setdefault(dedup_key(entry), set()).add(entry["source"])

    # Group entries by identity, keep best source
    best_entries: dict[tuple[str, str, bool], dict] = {}
    for entry in entries:
        key = dedup_key(entry)
        source_weight = assign_source_weight(entry["source"])
        existing = best_entries.get(key)
        if existing is None or source_weight > assign_source_weight(existing["source"]):
            best_entries[key] = entry.copy()

    # Compute final weights
    result = []
    for key, entry in best_entries.items():
        # Non-light-tone entries emit a single-spaced key; light-tone
        # entries keep their marker-derived double space.
        if "--" not in entry.get("kip_input", ""):
            entry["rime_key"] = " ".join(entry["rime_key"].split())
        base = assign_source_weight(entry["source"])
        length_mod = word_length_modifier(entry["hanlo"])
        overlap_bonus = 1.1 ** (len(key_sources[key]) - 1)

        # Corpus frequency boost: log-scale boost from observed usage.
        corpus_boost = 1.0
        kip = entry.get("kip_input", "")
        identity_count = identity_freq.get((entry["hanlo"], kip), 0)
        if identity_count > 0:
            corpus_boost = 1.0 + math.log10(1 + identity_count) * CORPUS_BOOST_COEFF
        elif kip and " ".join(entry["rime_key"].split()) in codes_with_identity:
            corpus_boost = 1.0  # identity data exists for this code; word unseen
        elif kip and kip in corpus_freq:
            corpus_boost = 1.0 + math.log10(1 + corpus_freq[kip]) * CORPUS_BOOST_COEFF

        entry["weight"] = int(base * length_mod * overlap_bonus * corpus_boost)
        result.append(entry)

    return result


# rime_key syllable tokens: split on spaces and hyphen runs (covers "--" light tone)
_SYLLABLE_SPLIT_RE = re.compile(r"[ \-]+")


def enforce_long_word_invariant(entries: list[dict], k: float = 1.2) -> tuple[list[dict], int]:
    syllable_best: dict[str, int] = {}
    for entry in entries:
        tokens = [t for t in _SYLLABLE_SPLIT_RE.split(entry["rime_key"]) if t]
        if len(tokens) == 1:
            weight = entry["weight"]
            if weight > syllable_best.get(tokens[0], 0):
                syllable_best[tokens[0]] = weight

    original_weight = {id(entry): entry["weight"] for entry in entries}

    # Group multi-syllable entries by code; the invariant is enforced per
    # group with a common offset: when the group's lightest member sits
    # below ceil(k * fragmented_sum), every member gains the same offset.
    # Relative gaps (and genuine ties) survive, and no member can end up
    # below the threshold. 長詞不敗 (AGENTS.md 設計原則 7).
    by_code: dict[str, list[dict]] = {}
    for entry in entries:
        tokens = [t for t in _SYLLABLE_SPLIT_RE.split(entry["rime_key"]) if t]
        if len(tokens) < 2:
            continue  # singles feed the thresholds; never re-ranked here
        by_code.setdefault(entry["rime_key"], []).append(entry)

    raised = 0
    for code_entries in by_code.values():
        tokens = [t for t in _SYLLABLE_SPLIT_RE.split(code_entries[0]["rime_key"]) if t]
        fragmented_sum = sum(syllable_best.get(token, 0) for token in tokens)
        if fragmented_sum <= 0:
            continue
        threshold = math.ceil(k * fragmented_sum)
        group_min = min(e["weight"] for e in code_entries)
        if group_min >= threshold:
            continue
        offset = threshold - group_min
        for entry in code_entries:
            entry["weight"] += offset
            if entry["weight"] > original_weight[id(entry)]:
                raised += 1

    return entries, raised


# Light-tone cap constants: mirror scripts/build_lighttone_entries.py's
# corpus-builder cap (margin 100, floor 300). PLAN 9-6 centralization will
# absorb them into a shared module.
_LT_CAP_MARGIN = 100
_LT_CAP_FLOOR = 300


def enforce_lighttone_cap(entries: list[dict]) -> int:
    """Cap light-tone rows below their plain parent (same text, same code).

    A double-space rime_key marks a light-tone variant (kì--tit). Core
    dictionary '--' rows reach the assembled dict with no cap at all, and
    the raise pass above can lift a LT row over parent-100; this pass is
    the single authority for "a parent outranks its light-tone variant".

    Parent lookup is per-identity — (hanlo, collapsed key): two texts may
    share a collapsed code, and each LT row is capped by its own text's
    parent, never by a code-max across texts. Rows without a same-text
    parent stay unchanged (corpus LT words whose plain form is absent).

    Returns:
        Number of rows whose weight changed.
    """
    parents: dict[tuple[str, str], int] = {}
    for entry in entries:
        if "  " in entry["rime_key"]:
            continue
        identity = (entry["hanlo"], " ".join(entry["rime_key"].split()))
        weight = entry["weight"]
        if weight > parents.get(identity, 0):
            parents[identity] = weight

    capped = 0
    for entry in entries:
        if "  " not in entry["rime_key"]:
            continue
        parent = parents.get((entry["hanlo"], " ".join(entry["rime_key"].split())))
        if parent is None:
            continue
        new_weight = max(_LT_CAP_FLOOR, min(entry["weight"], parent - _LT_CAP_MARGIN))
        if new_weight != entry["weight"]:
            entry["weight"] = new_weight
            capped += 1
    return capped


def enforce_dict_file_invariant(dict_path: Path, k: float = 1.2) -> int:
    """Enforce the long-word invariant on an assembled Rime dict.yaml.

    Reads the dict file, applies enforce_long_word_invariant to its data
    rows, then enforce_lighttone_cap so every light-tone row ranks below
    its parent even after the raise pass. Rewrites the file only when a
    weight changed. Use as the final pass after all append steps (phrases,
    light tone) so the whole assembled dictionary satisfies both rules.

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
        entries.append({"hanlo": parts[0], "rime_key": parts[1], "weight": int(parts[2])})
        row_index.append(i)

    _, raised = enforce_long_word_invariant(entries, k=k)
    capped = enforce_lighttone_cap(entries)

    if raised or capped:
        for entry, line_no in zip(entries, row_index, strict=True):
            parts = lines[line_no].split("\t")
            parts[2] = str(entry["weight"])
            lines[line_no] = "\t".join(parts)

        dict_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return raised


_VERSION_RE = re.compile(r'^version:\s*"?([^"\n]+)"?\s*$')


def write_word_keys(dict_path: Path, output_dir: Path) -> Path:
    """Snapshot a dict.yaml's (hanzi, key) set for release diffing (PLAN 9-2H).

    Writes ``word-keys-v<version>.tsv``: one header line plus sorted unique
    ``hanzi<TAB>key`` rows, no weights. Diffing two snapshots yields the exact
    word-level additions/removals between releases.

    Args:
        dict_path: Assembled dict.yaml (header carries the version).
        output_dir: Destination directory (created if missing).

    Returns:
        Path to the written snapshot file.
    """
    lines = dict_path.read_text(encoding="utf-8").splitlines()
    version = "unknown"
    pairs: set[tuple[str, str]] = set()
    for line in lines:
        version_match = _VERSION_RE.match(line)
        if version_match:
            version = version_match.group(1)
        parts = line.split("\t")
        if len(parts) >= 2 and "\t" in line and not line.startswith(("#", "---")):
            pairs.add((parts[0], parts[1]))

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"word-keys-v{version}.tsv"
    body = "\n".join(f"{hanlo}\t{key}" for hanlo, key in sorted(pairs))
    output_path.write_text(f"# word-keys v{version}\n{body}\n", encoding="utf-8")
    return output_path
