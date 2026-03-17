"""Build light-tone (輕聲) dictionary entries from corpus frequency data.

Scans corpus frequency TSV files for words containing the light tone marker `--`,
reverse-looks up their hanzi from the existing dictionary, and outputs new
dictionary entries to append to phah_taibun.dict.yaml.
"""

import argparse
import json
import math
import unicodedata
from pathlib import Path


def kip_to_rime_key(kip: str) -> str:
    """Convert kip_input to rime_key: -- becomes double space, - becomes single space.

    Args:
        kip: kip_input string (e.g., "tng2--lai5")

    Returns:
        rime_key string (e.g., "tng2  lai5")
    """
    result = kip.replace("--", "\x00")
    result = result.replace("-", " ")
    result = result.replace("\x00", "  ")
    return result


def unicode_tl_to_numeric(text: str) -> str:
    """Convert Unicode TL diacritics to numeric tone numbers.

    Decomposes text to NFD, replaces combining diacritical marks with tone
    numbers appended at the end of each syllable.

    Args:
        text: Text with TL diacritics (e.g., "lâi", "khí")

    Returns:
        Text with diacritics replaced by tone numbers (e.g., "lai5", "khi2")
    """
    if not text:
        return text

    diacritic_to_tone = {
        "\u0301": "2",  # acute accent -> tone 2
        "\u0300": "3",  # grave accent -> tone 3
        "\u0302": "5",  # circumflex -> tone 5
        "\u0304": "7",  # macron -> tone 7
        "\u030d": "8",  # vertical line above -> tone 8
    }

    decomposed = unicodedata.normalize("NFD", text)

    # Process syllable by syllable (split on hyphens to preserve structure)
    syllables = decomposed.split("-")
    result_syllables = []

    for syllable in syllables:
        tone = ""
        chars = []
        for ch in syllable:
            if ch in diacritic_to_tone:
                tone = diacritic_to_tone[ch]
            else:
                chars.append(ch)
        # Recompose the base characters and append tone number
        base = unicodedata.normalize("NFC", "".join(chars))
        result_syllables.append(base + tone)

    return "-".join(result_syllables)


def _rime_key_to_kip(rime_key: str) -> str:
    """Convert rime_key (space-separated) back to kip_input (hyphen-separated).

    Double space becomes `--`, single space becomes `-`.

    Args:
        rime_key: Rime key string (e.g., "tng2  lai5" or "tng2 lai5")

    Returns:
        kip_input string (e.g., "tng2--lai5" or "tng2-lai5")
    """
    # Replace double space with placeholder, then single space, then restore
    result = rime_key.replace("  ", "\x00")
    result = result.replace(" ", "-")
    result = result.replace("\x00", "--")
    return result


def load_dict(dict_path: Path) -> tuple[dict[str, set[str]], set[tuple[str, str]], dict[str, int]]:
    """Load existing dictionary into lookup tables.

    Parses phah_taibun.dict.yaml, skipping the YAML header (lines until ``...``).

    Args:
        dict_path: Path to phah_taibun.dict.yaml

    Returns:
        Tuple of:
        - kip_to_hanlo: maps kip_input (with hyphens, no ``--``) to set of hanlo strings
        - existing_rimekeys: set of (hanlo, rime_key) tuples for dedup
        - kip_to_weight: maps kip_input (no ``--``) to max weight for capping
    """
    kip_to_hanlo: dict[str, set[str]] = {}
    existing_rimekeys: set[tuple[str, str]] = set()
    kip_to_weight: dict[str, int] = {}

    in_header = True
    with open(dict_path, encoding="utf-8") as f:
        for line in f:
            if in_header:
                if line.strip() == "...":
                    in_header = False
                continue
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            hanlo, rime_key, weight_str = parts[0], parts[1], parts[2]
            try:
                weight = int(weight_str)
            except ValueError:
                weight = 0

            existing_rimekeys.add((hanlo, rime_key))

            # Convert rime_key to kip_input for lookup
            kip = _rime_key_to_kip(rime_key)
            kip_lower = kip.lower()

            # Only index non-light-tone entries for whole-word lookup
            if "--" not in kip_lower:
                kip_to_hanlo.setdefault(kip_lower, set()).add(hanlo)
                # Track max weight per kip for capping
                if kip_lower in kip_to_weight:
                    kip_to_weight[kip_lower] = max(kip_to_weight[kip_lower], weight)
                else:
                    kip_to_weight[kip_lower] = weight

    return kip_to_hanlo, existing_rimekeys, kip_to_weight


def load_lighttone_rules(rules_path: Path) -> dict[str, str]:
    """Load lighttone_rules.json and build suffix_hanzi mapping.

    Converts TL diacritics to numeric tones and maps suffix kip to hanzi.

    Args:
        rules_path: Path to lighttone_rules.json

    Returns:
        Dict mapping suffix kip (e.g., "lai5") to hanzi (e.g., "來").
        For multi-syllable suffixes: "khi2-lai5" -> "起來".
    """
    with open(rules_path, encoding="utf-8") as f:
        rules = json.load(f)

    suffix_hanzi: dict[str, str] = {}
    for rule in rules:
        tl = rule["tl"]  # e.g., "--lâi" or "--khí-lâi"
        hanzi = rule["hanzi"]

        # Strip leading --
        suffix_tl = tl.lstrip("-")
        # Convert unicode diacritics to numeric tones
        suffix_kip = unicode_tl_to_numeric(suffix_tl).lower()

        # Only store first mapping for each suffix (avoid overwriting)
        if suffix_kip not in suffix_hanzi:
            suffix_hanzi[suffix_kip] = hanzi

    return suffix_hanzi


def collect_lighttone_words(freq_paths: list[Path]) -> dict[str, int]:
    """Collect light-tone words from corpus frequency TSV files.

    Reads each TSV, collects entries where kip_input contains ``--``,
    and merges frequencies across files.

    Args:
        freq_paths: List of paths to corpus frequency TSV files

    Returns:
        Dict mapping normalized kip_input to summed frequency count
    """
    merged: dict[str, int] = {}

    for freq_path in freq_paths:
        if not freq_path.exists():
            continue
        with open(freq_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) < 2:
                    continue
                kip = parts[0].lower()
                if "--" not in kip:
                    continue
                # Skip entries that look malformed (trailing --, parentheses, etc.)
                if kip.endswith("--") or "(" in kip:
                    continue
                try:
                    count = int(parts[1])
                except ValueError:
                    continue
                merged[kip] = merged.get(kip, 0) + count

    return merged


def _count_syllables(kip_segment: str) -> int:
    """Count syllables in a kip segment (hyphen-separated).

    Args:
        kip_segment: A kip_input segment without ``--`` (e.g., "tng2" or "khi2-lai5")

    Returns:
        Number of syllables
    """
    if not kip_segment:
        return 0
    return len(kip_segment.split("-"))


def _count_hanlo_chars(hanlo: str) -> int:
    """Count logical characters in a hanlo string.

    CJK characters count as 1. Romanization syllables are identified by
    contiguous non-CJK non-separator characters.

    For simplicity, we count: CJK chars + romanization 'words' separated by
    hyphens or spaces. But since hanlo from the dict doesn't have separators
    between CJK chars, we just count CJK chars plus any romanization tokens.

    Args:
        hanlo: Han-Lo text (e.g., "轉來" or "去lih")

    Returns:
        Character/syllable count
    """
    count = 0
    in_roman = False
    for ch in hanlo:
        cat = unicodedata.category(ch)
        if cat.startswith("Lo"):
            # CJK ideograph
            count += 1
            in_roman = False
        elif ch in ("-", " "):
            if in_roman:
                in_roman = False
        elif cat.startswith("L") or cat.startswith("N") or cat.startswith("M"):
            if not in_roman:
                count += 1
                in_roman = True
        else:
            in_roman = False
    return count


def insert_lighttone_marker(hanlo: str, prefix_syllable_count: int) -> str:
    """Insert ``--`` into hanzi string at the correct syllable position.

    Args:
        hanlo: Han-Lo text without ``--`` (e.g., "轉來")
        prefix_syllable_count: Number of syllables before ``--`` (e.g., 1)

    Returns:
        Han-Lo text with ``--`` inserted (e.g., "轉--來")
    """
    # Walk through hanlo counting logical characters/syllables
    pos = 0
    char_count = 0
    in_roman = False

    for i, ch in enumerate(hanlo):
        cat = unicodedata.category(ch)
        if cat.startswith("Lo"):
            char_count += 1
            in_roman = False
            if char_count == prefix_syllable_count:
                pos = i + 1
                break
        elif ch in ("-", " "):
            if in_roman:
                in_roman = False
                if char_count == prefix_syllable_count:
                    pos = i
                    break
        elif cat.startswith("L") or cat.startswith("N") or cat.startswith("M"):
            if not in_roman:
                char_count += 1
                in_roman = True
        else:
            if in_roman:
                in_roman = False
                if char_count == prefix_syllable_count:
                    pos = i
                    break
    else:
        # Reached end of string
        if in_roman and char_count == prefix_syllable_count:
            pos = len(hanlo)

    if pos == 0 and prefix_syllable_count > 0:
        return hanlo  # Could not find position; return unchanged

    return hanlo[:pos] + "--" + hanlo[pos:]


def compute_lighttone_weight(count: int, non_lighttone_weight: int | None) -> int:
    """Compute weight for a light-tone entry.

    Uses log-scale formula capped within bounds, and further capped below
    the non-light-tone variant's weight.

    Args:
        count: Corpus frequency count
        non_lighttone_weight: Weight of the non-light-tone variant (or None)

    Returns:
        Computed weight (int)
    """
    raw = int(300 + math.log10(1 + count) * 150)
    weight = min(1500, max(300, raw))

    if non_lighttone_weight is not None:
        weight = min(weight, non_lighttone_weight - 100)
        # Ensure minimum of 300 even after capping
        weight = max(300, weight)

    return weight


def reverse_lookup_hanzi(
    kip_input: str,
    kip_to_hanlo: dict[str, set[str]],
    suffix_hanzi: dict[str, str],
) -> list[str]:
    """Reverse-lookup hanzi for a light-tone kip_input.

    Tries whole-word match first, then syllable assembly.

    Args:
        kip_input: Light-tone kip_input (e.g., "tng2--lai5")
        kip_to_hanlo: Dict mapping non-light-tone kip to hanlo set
        suffix_hanzi: Dict mapping suffix kip to hanzi

    Returns:
        List of hanlo strings with ``--`` inserted (e.g., ["轉--來"])
    """
    results = []

    # Split at --
    parts = kip_input.split("--")
    if len(parts) != 2:
        return results

    prefix_kip = parts[0]  # e.g., "tng2"
    suffix_kip = parts[1]  # e.g., "lai5"

    if not prefix_kip or not suffix_kip:
        return results

    prefix_syllable_count = _count_syllables(prefix_kip)

    # Strategy 1: Whole-word match
    whole_kip = prefix_kip + "-" + suffix_kip
    if whole_kip in kip_to_hanlo:
        for hanlo in kip_to_hanlo[whole_kip]:
            marked = insert_lighttone_marker(hanlo, prefix_syllable_count)
            if "--" in marked and marked != hanlo:
                results.append(marked)

    if results:
        return results

    # Strategy 2: Syllable assembly
    prefix_hanzi_set = kip_to_hanlo.get(prefix_kip, set())
    # Get suffix hanzi from lighttone_rules first, then dict
    suffix_hz = suffix_hanzi.get(suffix_kip)
    if suffix_hz is None:
        suffix_candidates = kip_to_hanlo.get(suffix_kip, set())
        if len(suffix_candidates) == 1:
            suffix_hz = next(iter(suffix_candidates))

    if prefix_hanzi_set and suffix_hz is not None:
        for prefix_hz in prefix_hanzi_set:
            assembled = prefix_hz + "--" + suffix_hz
            results.append(assembled)

    return results


def build_lighttone_entries(
    dict_path: Path,
    rules_path: Path,
    freq_paths: list[Path],
) -> list[dict[str, str | int]]:
    """Build light-tone dictionary entries.

    Main orchestration function that loads data, performs lookups, and
    generates entries.

    Args:
        dict_path: Path to phah_taibun.dict.yaml
        rules_path: Path to lighttone_rules.json
        freq_paths: List of corpus frequency TSV paths

    Returns:
        List of dicts with keys: hanlo, rime_key, weight
    """
    kip_to_hanlo, existing_rimekeys, kip_to_weight = load_dict(dict_path)
    suffix_hanzi = load_lighttone_rules(rules_path)
    lighttone_words = collect_lighttone_words(freq_paths)

    new_entries: list[dict[str, str | int]] = []
    seen: set[tuple[str, str]] = set()

    for kip_input, count in sorted(lighttone_words.items(), key=lambda x: -x[1]):
        hanlo_candidates = reverse_lookup_hanzi(kip_input, kip_to_hanlo, suffix_hanzi)

        if not hanlo_candidates:
            continue

        rime_key = kip_to_rime_key(kip_input)

        # Find non-light-tone variant weight for capping
        non_lt_kip = kip_input.replace("--", "-")
        non_lt_weight = kip_to_weight.get(non_lt_kip)

        weight = compute_lighttone_weight(count, non_lt_weight)

        for hanlo in hanlo_candidates:
            key = (hanlo, rime_key)
            if key in existing_rimekeys or key in seen:
                continue
            seen.add(key)
            new_entries.append(
                {
                    "hanlo": hanlo,
                    "rime_key": rime_key,
                    "weight": weight,
                }
            )

    return new_entries


def write_entries(entries: list[dict[str, str | int]], output_path: Path) -> None:
    """Write light-tone entries to a TSV file.

    Args:
        entries: List of dicts with keys: hanlo, rime_key, weight
        output_path: Path to output TSV file
    """
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(f"{entry['hanlo']}\t{entry['rime_key']}\t{entry['weight']}\n")


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for building light-tone dictionary entries."""
    parser = argparse.ArgumentParser(description="Build light-tone dictionary entries from corpus frequency data")
    parser.add_argument("--dict", type=Path, required=True, help="Path to phah_taibun.dict.yaml")
    parser.add_argument("--rules", type=Path, required=True, help="Path to lighttone_rules.json")
    parser.add_argument(
        "--corpus-freq",
        type=Path,
        nargs="*",
        default=[],
        help="Corpus freq TSV files",
    )
    parser.add_argument("--output", type=Path, required=True, help="Output: entries to append")
    args = parser.parse_args(argv)

    entries = build_lighttone_entries(args.dict, args.rules, args.corpus_freq)
    write_entries(entries, args.output)
    print(f"Written {len(entries)} light-tone entries to {args.output}")


if __name__ == "__main__":
    main()
