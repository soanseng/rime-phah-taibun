"""Heuristic frequency weighting for Rime dictionary entries.

Assigns weights based on source authority, word length, cross-source overlap,
and optional corpus frequency data.
"""

import math
import unicodedata
from pathlib import Path

SOURCE_WEIGHTS = {
    "moe": 1000,  # L1: 教育部辭典
    "itaigi": 800,  # L2: iTaigi (群眾驗證)
    "taihoa": 500,  # L3: 台華線頂
    "taijit": 200,  # L4: 台日大辭典
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
