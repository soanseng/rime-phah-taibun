"""Heuristic frequency weighting for Rime dictionary entries.

Assigns weights based on source authority, word length, and cross-source overlap.
"""

import unicodedata

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


def compute_weights(entries: list[dict]) -> list[dict]:
    """Compute final frequency weights for dictionary entries.

    Combines source authority, word length modifier, and cross-source overlap bonus.

    Args:
        entries: List of dicts with hanlo, rime_key, source fields

    Returns:
        Deduplicated list with computed 'weight' field (int)
    """
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
        entry["weight"] = int(base * length_mod * overlap_bonus)
        result.append(entry)

    return result
