"""Build Mandarin→Taiwanese (華→台) mapping from ChhoeTaigi data.

Reads ChhoeTaigi CSVs, extracts HoaBun (華語) → KipInput (TL) mappings,
and outputs a simple TSV file for Lua to load at runtime.

This enables the reverse lookup flow:
  注音反查 → 華語字 → 查 hoabun_map → 台語TL碼 → 送回主輸入 → 台語字
"""

import argparse
import csv
import re
import sys
from pathlib import Path

# Source priority: higher = more authoritative
SOURCE_PRIORITY = {
    "moe": 4,       # 教育部台語辭典
    "itaigi": 3,     # iTaigi 社群
    "taihoa": 2,     # 台華線頂
    "maryknoll": 1,  # Maryknoll
}

CSV_SOURCE_MAP = {
    "iTaigiHoataiTuichiautian": "itaigi",
    "TaihoaSoanntengTuichiautian": "taihoa",
    "KauiokpooTaigiSutian": "moe",
    "MaryknollTaiengSutian": "maryknoll",
}


def cjk_len(text: str) -> int:
    """Count characters (not bytes) in a string."""
    return len(text)


def clean_kip_input(kip_input: str) -> str | None:
    """Clean KipInput: remove markers, take first variant."""
    text = kip_input.strip()
    if not text:
        return None
    # Remove common markers: (替), (白), (文), (俗), (雅)
    text = re.sub(r"\([替白文俗雅]\)", "", text).strip()
    # Take first variant if slash-separated
    if "/" in text:
        text = text.split("/")[0].strip()
    if not text:
        return None
    # Must look like valid TL romanization (lowercase letters, digits, hyphens)
    if not re.match(r"^[a-z0-9][a-z0-9 \-]*$", text):
        return None
    return text


def split_hoabun(hoabun: str) -> list[str]:
    """Split HoaBun into individual Mandarin words.

    Handles delimiters: 、；，,;
    Filters out sentences and non-CJK text.
    """
    if not hoabun:
        return []
    # Remove parenthetical notes like (文), (白), (俗), etc.
    text = re.sub(r"\([^)]*\)", "", hoabun).strip()
    # Skip if it looks like a sentence (has sentence-ending punctuation)
    if re.search(r"[。！？；：]", text):
        return []
    # Split on common delimiters
    parts = re.split(r"[、，,;]", text)
    result = []
    for part in parts:
        word = part.strip()
        if not word:
            continue
        # Must contain at least one CJK character
        if not re.search(r"[\u4e00-\u9fff\u3400-\u4dbf]", word):
            continue
        # Skip if too long (likely a definition, not a word)
        if cjk_len(word) > 6:
            continue
        result.append(word)
    return result


def split_into_chars(
    hoabun: str, kip_input: str
) -> list[tuple[str, str]]:
    """Split a multi-char HoaBun into individual character→syllable mappings.

    Only works when char count matches syllable count.
    E.g., "吃飯" + "tsiah8-png7" → [("吃", "tsiah8"), ("飯", "png7")]
    """
    # Extract CJK characters from hoabun
    chars = re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", hoabun)
    if len(chars) < 2:
        return []
    # Split KipInput into syllables
    syllables = kip_input.split("-")
    if len(syllables) != len(chars):
        return []
    return list(zip(chars, syllables))


def _read_csv_rows(data_dir: Path) -> list[tuple[str, str, int, str]]:
    """Read all ChhoeTaigi CSVs and return (hoabun, kip, priority, hanlo) tuples."""
    rows = []
    for csv_path in sorted(data_dir.glob("ChhoeTaigi_*.csv")):
        source = None
        for key, src_name in CSV_SOURCE_MAP.items():
            if key in csv_path.name:
                source = src_name
                break
        if source is None:
            continue

        priority = SOURCE_PRIORITY.get(source, 0)

        with open(csv_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                hoabun = row.get("HoaBun", "").strip()
                if not hoabun:
                    continue
                kip_raw = row.get("KipInput", "").strip()
                if not kip_raw:
                    kip_raw = row.get("PojInput", "").strip()
                kip = clean_kip_input(kip_raw)
                if not kip:
                    continue
                hanlo = row.get("HanLoTaibunKip", "").strip()
                if not hanlo:
                    hanlo = row.get("HanLoTaibunPoj", "").strip()
                rows.append((hoabun, kip, priority, hanlo))
    return rows


def extract_hoabun_mappings(data_dir: Path) -> dict[str, tuple[str, int]]:
    """Extract HoaBun → KipInput mappings from all ChhoeTaigi CSVs.

    Two-pass approach:
      Pass 1: Word-level mappings (semantically accurate)
      Pass 2: Character-level splits (fill gaps for single chars)

    Returns:
        Dict mapping Mandarin word → (kip_input_space_separated, priority)
    """
    mappings: dict[str, tuple[str, int]] = {}

    def add_mapping(
        mandarin: str, kip: str, priority: int, *, is_primary: bool = False
    ) -> None:
        existing = mappings.get(mandarin)
        if existing is None:
            mappings[mandarin] = (kip, priority, is_primary)
            return
        old_kip, old_pri, old_primary = existing
        # Primary entries (HoaBun == the word itself) beat synonym entries
        if is_primary and not old_primary:
            mappings[mandarin] = (kip, priority, is_primary)
            return
        if not is_primary and old_primary:
            return  # keep primary
        # Prefer entries where syllable count matches CJK character count
        char_count = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", mandarin))
        if char_count > 0:
            new_syls = len(kip.split())
            old_syls = len(old_kip.split())
            new_match = new_syls == char_count
            old_match = old_syls == char_count
            if new_match and not old_match:
                mappings[mandarin] = (kip, priority, is_primary)
                return
            if not new_match and old_match:
                return
        if priority > old_pri:
            mappings[mandarin] = (kip, priority, is_primary)

    rows = _read_csv_rows(data_dir)

    # Pass 1: Word-level mappings (the HoaBun text as-is)
    for hoabun, kip, priority, hanlo in rows:
        rime_key = kip.replace("-", " ")
        words = split_hoabun(hoabun)
        for mandarin_word in words:
            # "Primary" = the HoaBun is exactly this word (not part of a list)
            # or the Taiwanese HanLo contains similar characters
            is_primary = len(words) == 1 or mandarin_word == hanlo
            add_mapping(mandarin_word, rime_key, priority, is_primary=is_primary)

    # Pass 2: Character-level splits — only for chars NOT already mapped
    for hoabun, kip, priority, _hanlo in rows:
        for mandarin_word in split_hoabun(hoabun):
            for char, syl in split_into_chars(mandarin_word, kip):
                if char not in mappings:
                    add_mapping(char, syl, priority)

    return mappings


def build_hoabun_map(data_dir: Path, output_path: Path) -> int:
    """Build the hoabun_map.txt file.

    Args:
        data_dir: Path to ChhoeTaigiDatabase directory
        output_path: Path to write hoabun_map.txt

    Returns:
        Number of entries written
    """
    mappings = extract_hoabun_mappings(data_dir)

    # Sort by Mandarin word for deterministic output
    sorted_entries = sorted(mappings.items())

    with open(output_path, "w", encoding="utf-8") as f:
        for mandarin, entry in sorted_entries:
            f.write(f"{mandarin}\t{entry[0]}\n")

    return len(sorted_entries)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Build Mandarin→Taiwanese mapping from ChhoeTaigi data"
    )
    parser.add_argument(
        "--input", type=Path, required=True,
        help="Path to ChhoeTaigiDatabase directory",
    )
    parser.add_argument(
        "--output", type=Path, required=True,
        help="Output path for hoabun_map.txt",
    )
    args = parser.parse_args(argv)

    data_dir = args.input / "ChhoeTaigiDatabase"
    if not data_dir.exists():
        data_dir = args.input

    if not any(data_dir.glob("ChhoeTaigi_*.csv")):
        print(f"Error: No ChhoeTaigi CSV files found in {data_dir}", file=sys.stderr)
        sys.exit(1)

    count = build_hoabun_map(data_dir, args.output)
    print(f"Written {count} entries to {args.output}")


if __name__ == "__main__":
    main()
