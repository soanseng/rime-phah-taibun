"""Convert ChhoeTaigi CSV dictionaries to Rime dict.yaml format.

Reads iTaigi (CC0), 台華線頂 (CC BY-SA), and additional ChhoeTaigi CSVs,
extracts pronunciation and Han-Lo writing data, and outputs Rime-compatible
dictionary entries.
"""

import argparse
import csv
import re
import sys
import unicodedata
from pathlib import Path
from typing import TextIO

try:
    from scripts.tl_poj_convert import poj_to_tl, tl_to_poj
except ModuleNotFoundError:
    from tl_poj_convert import poj_to_tl, tl_to_poj

CSV_SOURCE_MAP = {
    "iTaigiHoataiTuichiautian": "itaigi",
    "TaihoaSoanntengTuichiautian": "taihoa",
    "KauiokpooTaigiSutian": "moe",
    "TaijitToaSutian": "taijit",
    "MaryknollTaiengSutian": "maryknoll",
    "EmbreeTaiengSutian": "embree",
    "KamJitian": "kamjitian",
    "TaioanPehoeKichhooGiku": "pehoe",
    "TaioanSitbutMialui": "sitbut",
}

COMBINING_TONE_TO_NUMBER = {
    "\u0301": "2",  # acute accent
    "\u0300": "3",  # grave accent
    "\u0302": "5",  # circumflex
    "\u0304": "7",  # macron
    "\u030d": "8",  # vertical line above
    "\u030b": "9",  # double acute accent
    "\u0306": "9",  # breve
}


def unicode_tones_to_numeric(text: str) -> str:
    """Normalize Unicode TL/POJ tone marks to syllable-final tone numbers."""
    if not text:
        return text

    text = text.replace("\u3000", " ").replace("ⁿ", "nn")
    text = re.sub(r"\s+", "-", text.strip())

    parts = re.split(r"(-+)", text)
    normalized_parts: list[str] = []
    for part in parts:
        if not part or set(part) == {"-"}:
            normalized_parts.append(part)
            continue

        decomposed = unicodedata.normalize("NFD", part)
        tone = ""
        chars = []
        for ch in decomposed:
            if ch in COMBINING_TONE_TO_NUMBER:
                tone = COMBINING_TONE_TO_NUMBER[ch]
            else:
                chars.append(ch)
        base = unicodedata.normalize("NFC", "".join(chars)).replace("\u0131", "i").lower()
        base = base.replace("o\u0358", "oo")
        if tone and not re.search(r"[1-9]$", base):
            base += tone
        normalized_parts.append(base)

    return "".join(normalized_parts)


def is_valid_kip_input(kip_input: str) -> bool:
    """Return whether a normalized KipInput variant is usable as a Rime key."""
    return bool(re.fullmatch(r"[a-z0-9]+(?:-+[a-z0-9]+)*", kip_input))


def clean_hanlo_text(text: str) -> str:
    """Remove TSV-breaking control whitespace from candidate text."""
    return re.sub(r"[\t\r\n]+", "", text).strip()


def normalize_implicit_tone(kip_input: str) -> str:
    """Add explicit tone numbers to syllables that have no tone number.

    ChhoeTaigi stores default tones as bare syllables:
    - 舒聲 (open/nasal ending: vowel, m, n, ng) → tone 1 (陰平)
    - 入聲 (checked ending: p, t, k, h) → tone 4 (陰入)

    Rime needs explicit tone numbers so users can type "to1" or "tsit4"
    to narrow candidates to a specific tone.

    Args:
        kip_input: KipInput string like "to-sit" or "tua7-lang5"

    Returns:
        String with implicit tones made explicit: "to1-sit4" or "tua7-lang5"
    """
    syllables = kip_input.split("-")
    result = []
    for s in syllables:
        if s and re.match(r"^[a-z]+$", s):
            # 入聲: ends in p, t, k, h → tone 4
            if re.search(r"[ptkh]$", s):
                result.append(s + "4")
            # 舒聲: ends in vowel, m, n, ng → tone 1
            else:
                result.append(s + "1")
        else:
            result.append(s)
    return "-".join(result)


def strip_tone_numbers(kip_input: str, delimiter: str = "-") -> str:
    """Remove tone number suffixes (1-9) from each syllable in KipInput.

    Args:
        kip_input: KipInput string like "tua7-lang5" or "tsit8"
        delimiter: Output delimiter between syllables (default "-", use " " for Rime)

    Returns:
        Toneless string like "tua-lang" or "tsit"
    """
    syllables = kip_input.split("-")
    stripped = [re.sub(r"[1-9]$", "", s) for s in syllables]
    return delimiter.join(stripped)


def clean_kip_input(kip_input: str) -> list[str]:
    """Clean and split KipInput into individual pronunciation variants.

    Handles:
    - (替) marker removal
    - Slash-separated multiple readings split into separate entries
    - Empty/whitespace inputs

    Args:
        kip_input: Raw KipInput string from ChhoeTaigi CSV

    Returns:
        List of cleaned KipInput strings (may be multiple for slash-separated)
    """
    text = kip_input.strip()
    if not text:
        return []
    # Remove (替) marker
    text = re.sub(r"\(替\)", "", text)
    # Split on "/" for multiple readings
    variants = []
    for variant in (unicode_tones_to_numeric(v.strip()) for v in text.split("/") if v.strip()):
        if is_valid_kip_input(variant):
            variants.append(variant)
    return variants


def parse_itaigi_csv(csvfile: TextIO) -> list[dict]:
    """Parse iTaigi CSV into structured dictionary entries.

    Args:
        csvfile: File-like object containing iTaigi CSV data

    Returns:
        List of dicts with keys: hanlo, kip_input, rime_key, hoabun, source
    """
    entries = []
    reader = csv.DictReader(csvfile)
    for row in reader:
        kip_raw = row.get("KipInput", "").strip()
        hanlo = clean_hanlo_text(row.get("HanLoTaibunKip", ""))
        hoabun = row.get("HoaBun", "").strip()
        if not kip_raw or not hanlo:
            continue
        for kip in clean_kip_input(kip_raw):
            entries.append(
                {
                    "hanlo": hanlo,
                    "kip_input": kip,
                    "rime_key": normalize_implicit_tone(kip).replace("-", " "),
                    "hoabun": hoabun,
                    "source": "itaigi",
                }
            )
    return entries


def parse_taihoa_csv(csvfile: TextIO) -> list[dict]:
    """Parse 台華線頂 CSV into structured dictionary entries.

    Handles KipInputOthers column for variant pronunciations.

    Args:
        csvfile: File-like object containing 台華線頂 CSV data

    Returns:
        List of dicts with keys: hanlo, kip_input, rime_key, hoabun, source
    """
    entries = []
    reader = csv.DictReader(csvfile)
    for row in reader:
        kip_raw = row.get("KipInput", "").strip()
        kip_others = row.get("KipInputOthers", "").strip()
        hanlo = clean_hanlo_text(row.get("HanLoTaibunKip", ""))
        hoabun = row.get("HoaBun", "").strip()
        if not hanlo:
            continue
        # Process main KipInput
        if kip_raw:
            for kip in clean_kip_input(kip_raw):
                entries.append(
                    {
                        "hanlo": hanlo,
                        "kip_input": kip,
                        "rime_key": normalize_implicit_tone(kip).replace("-", " "),
                        "hoabun": hoabun,
                        "source": "taihoa",
                    }
                )
        # Process Others variants
        if kip_others:
            for kip in clean_kip_input(kip_others):
                entries.append(
                    {
                        "hanlo": hanlo,
                        "kip_input": kip,
                        "rime_key": normalize_implicit_tone(kip).replace("-", " "),
                        "hoabun": hoabun,
                        "source": "taihoa",
                    }
                )
    return entries


def parse_generic_csv(csvfile: TextIO, source_name: str) -> list[dict]:
    """Parse a generic ChhoeTaigi CSV into structured dictionary entries.

    Handles CSVs with varying column names by trying KipInput first,
    then falling back to PojInput. Similarly tries HanLoTaibunKip
    before HanLoTaibunPoj.

    Args:
        csvfile: File-like object containing CSV data
        source_name: Source identifier for the entries (e.g. "maryknoll")

    Returns:
        List of dicts with keys: hanlo, kip_input, rime_key, hoabun, source
    """
    entries = []
    reader = csv.DictReader(csvfile)
    for row in reader:
        # Try KipInput, fall back to PojInput
        kip_raw = row.get("KipInput", "").strip()
        is_poj_input = False
        if not kip_raw:
            kip_raw = row.get("PojInput", "").strip()
            is_poj_input = True
        # Try HanLoTaibunKip, fall back to HanLoTaibunPoj
        hanlo = clean_hanlo_text(row.get("HanLoTaibunKip", ""))
        if not hanlo:
            hanlo = clean_hanlo_text(row.get("HanLoTaibunPoj", ""))
        hoabun = row.get("HoaBun", "").strip()
        if not kip_raw or not hanlo:
            continue
        for kip in clean_kip_input(kip_raw):
            if is_poj_input:
                kip = poj_to_tl(kip)
            entries.append(
                {
                    "hanlo": hanlo,
                    "kip_input": kip,
                    "rime_key": normalize_implicit_tone(kip).replace("-", " "),
                    "hoabun": hoabun,
                    "source": source_name,
                }
            )
    return entries


def _clean_kipsutian_reading(reading: str) -> str:
    reading = re.sub(r"[\uFF08(][^\uFF09)]*[\uFF09)]", "", reading)
    reading = re.sub(r"\u3010[^\u3011]*\u3011", "", reading)
    return reading.strip()


def parse_kipsutian_main_csv(csvfile: TextIO, include_roman_outputs: bool = True) -> list[dict]:
    """Parse MOE KipSutian CSV into main input dictionary entries.

    The upstream ``漢字`` field is kept as the primary candidate, including
    Han-Lo mixed entries when the source uses them. Full romanization TL and
    POJ candidates are added as selectable output forms for the same input key.
    """
    entries = []
    reader = csv.DictReader(csvfile)
    for row in reader:
        hanlo = clean_hanlo_text(row.get("漢字", ""))
        reading_raw = row.get("羅馬字", "").strip()
        if not hanlo or not reading_raw:
            continue

        reading_variants = [_clean_kipsutian_reading(v) for v in reading_raw.split("/") if v.strip()]
        for reading_variant in reading_variants:
            for kip in clean_kip_input(reading_variant):
                rime_key = normalize_implicit_tone(kip).replace("-", " ")
                entries.append(
                    {
                        "hanlo": hanlo,
                        "kip_input": kip,
                        "rime_key": rime_key,
                        "hoabun": "",
                        "source": "moe",
                    }
                )
                if include_roman_outputs:
                    tl_output = clean_hanlo_text(reading_variant)
                    poj_output = clean_hanlo_text(tl_to_poj(reading_variant))
                    entries.append(
                        {
                            "hanlo": tl_output,
                            "kip_input": kip,
                            "rime_key": rime_key,
                            "hoabun": "",
                            "source": "moe_tl",
                        }
                    )
                    entries.append(
                        {
                            "hanlo": poj_output,
                            "kip_input": kip,
                            "rime_key": rime_key,
                            "hoabun": "",
                            "source": "moe_poj",
                        }
                    )
    return entries


def source_name_from_filename(filename: str) -> str | None:
    """Extract the source name from a ChhoeTaigi CSV filename.

    Args:
        filename: CSV filename like "ChhoeTaigi_KamJitian.csv"

    Returns:
        Source name string or None if filename doesn't match any known CSV
    """
    for key, source in CSV_SOURCE_MAP.items():
        if key in filename:
            return source
    return None


def dedup_entries(entries: list[dict]) -> list[dict]:
    """Remove duplicate entries with same hanlo and rime_key.

    Args:
        entries: List of dictionary entries

    Returns:
        Deduplicated list
    """
    seen: set[tuple[str, str]] = set()
    result = []
    for entry in entries:
        key = (entry["hanlo"], entry["rime_key"])
        if key not in seen:
            seen.add(key)
            result.append(entry)
    return result


def write_rime_dict(entries: list[dict], output_path: Path) -> None:
    """Write dictionary entries to Rime dict.yaml format.

    Args:
        entries: List of dicts with keys: hanlo, rime_key, weight
        output_path: Path to write the dict.yaml file
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write("name: phah_taibun\n")
        f.write('version: "0.1.0"\n')
        f.write("sort: by_weight\n")
        f.write("use_preset_vocabulary: false\n")
        f.write("...\n")
        for entry in entries:
            weight = entry.get("weight", 0)
            f.write(f"{entry['hanlo']}\t{entry['rime_key']}\t{weight}\n")


def convert_chhoetaigi(
    itaigi_paths: list[Path],
    taihoa_paths: list[Path],
    output_path: Path,
    corpus_freq: dict[str, int] | None = None,
    generic_paths: list[tuple[Path, str]] | None = None,
    kipsutian_paths: list[Path] | None = None,
) -> None:
    """Convert ChhoeTaigi CSV files to Rime dict.yaml.

    Uses heuristic frequency weighting from build_frequency module.

    Args:
        itaigi_paths: Paths to iTaigi CSV files
        taihoa_paths: Paths to 台華線頂 CSV files
        output_path: Path to write output dict.yaml
        corpus_freq: Optional merged corpus frequency dict (kip_input → count)
        generic_paths: Optional list of (path, source_name) tuples for additional CSVs
        kipsutian_paths: Optional KipSutian kautian.csv files to include in the main dictionary
    """
    try:
        from scripts.build_frequency import compute_weights
    except ModuleNotFoundError:
        from build_frequency import compute_weights

    all_entries = []
    for path in itaigi_paths:
        with open(path, encoding="utf-8-sig") as f:
            all_entries.extend(parse_itaigi_csv(f))
    for path in taihoa_paths:
        with open(path, encoding="utf-8-sig") as f:
            all_entries.extend(parse_taihoa_csv(f))
    for path, source_name in generic_paths or []:
        with open(path, encoding="utf-8-sig") as f:
            all_entries.extend(parse_generic_csv(f, source_name))
    for path in kipsutian_paths or []:
        with open(path, encoding="utf-8-sig") as f:
            all_entries.extend(parse_kipsutian_main_csv(f))
    weighted = compute_weights(all_entries, corpus_freq=corpus_freq)
    write_rime_dict(weighted, output_path)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for ChhoeTaigi dictionary conversion."""
    try:
        from scripts.build_frequency import load_corpus_frequencies
    except ModuleNotFoundError:
        from build_frequency import load_corpus_frequencies

    parser = argparse.ArgumentParser(description="Convert ChhoeTaigi CSV to Rime dict.yaml")
    parser.add_argument("--input", type=Path, required=True, help="Path to ChhoeTaigiDatabase directory")
    parser.add_argument("--output", type=Path, required=True, help="Output directory for dict.yaml files")
    parser.add_argument(
        "--corpus-freq",
        type=Path,
        nargs="*",
        default=[],
        help="Paths to corpus frequency TSV files (word\\tcount)",
    )
    parser.add_argument(
        "--kipsutian-csv",
        type=Path,
        action="append",
        default=[],
        help="Path to KipSutian kautian.csv to include in the main dictionary",
    )
    args = parser.parse_args(argv)

    data_dir = args.input / "ChhoeTaigiDatabase"
    if not data_dir.exists():
        data_dir = args.input

    itaigi = data_dir / "ChhoeTaigi_iTaigiHoataiTuichiautian.csv"
    taihoa = data_dir / "ChhoeTaigi_TaihoaSoanntengTuichiautian.csv"

    itaigi_paths = [itaigi] if itaigi.exists() else []
    taihoa_paths = [taihoa] if taihoa.exists() else []

    # Auto-discover additional CSVs
    known_special = {itaigi.name, taihoa.name}
    generic_paths: list[tuple[Path, str]] = []
    for csv_path in sorted(data_dir.glob("ChhoeTaigi_*.csv")):
        if csv_path.name in known_special:
            continue
        source = source_name_from_filename(csv_path.name)
        if source is not None:
            generic_paths.append((csv_path, source))

    if not itaigi_paths and not taihoa_paths and not generic_paths:
        print(f"Error: No CSV files found in {data_dir}", file=sys.stderr)
        sys.exit(1)

    # Merge corpus frequency files
    corpus_freq: dict[str, int] | None = None
    if args.corpus_freq:
        corpus_freq = {}
        for freq_path in args.corpus_freq:
            freqs = load_corpus_frequencies(freq_path)
            for word, count in freqs.items():
                corpus_freq[word] = corpus_freq.get(word, 0) + count

    args.output.mkdir(parents=True, exist_ok=True)
    output_path = args.output / "phah_taibun.dict.yaml"
    convert_chhoetaigi(
        itaigi_paths,
        taihoa_paths,
        output_path,
        corpus_freq=corpus_freq,
        generic_paths=generic_paths,
        kipsutian_paths=args.kipsutian_csv,
    )
    print(f"Written: {output_path}")


if __name__ == "__main__":
    main()
