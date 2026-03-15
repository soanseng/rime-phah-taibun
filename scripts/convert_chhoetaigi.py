"""Convert ChhoeTaigi CSV dictionaries to Rime dict.yaml format.

Reads iTaigi (CC0) and 台華線頂 (CC BY-SA) CSVs, extracts pronunciation
and Han-Lo writing data, and outputs Rime-compatible dictionary entries.
"""

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import TextIO


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
    variants = [v.strip() for v in text.split("/") if v.strip()]
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
        hanlo = row.get("HanLoTaibunKip", "").strip()
        hoabun = row.get("HoaBun", "").strip()
        if not kip_raw or not hanlo:
            continue
        for kip in clean_kip_input(kip_raw):
            entries.append(
                {
                    "hanlo": hanlo,
                    "kip_input": kip,
                    "rime_key": strip_tone_numbers(kip, delimiter=" "),
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
        hanlo = row.get("HanLoTaibunKip", "").strip()
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
                        "rime_key": strip_tone_numbers(kip, delimiter=" "),
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
                        "rime_key": strip_tone_numbers(kip, delimiter=" "),
                        "hoabun": hoabun,
                        "source": "taihoa",
                    }
                )
    return entries


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
) -> None:
    """Convert ChhoeTaigi CSV files to Rime dict.yaml.

    Uses heuristic frequency weighting from build_frequency module.

    Args:
        itaigi_paths: Paths to iTaigi CSV files
        taihoa_paths: Paths to 台華線頂 CSV files
        output_path: Path to write output dict.yaml
        corpus_freq: Optional merged corpus frequency dict (kip_input → count)
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
    args = parser.parse_args(argv)

    data_dir = args.input / "ChhoeTaigiDatabase"
    if not data_dir.exists():
        data_dir = args.input

    itaigi = data_dir / "ChhoeTaigi_iTaigiHoataiTuichiautian.csv"
    taihoa = data_dir / "ChhoeTaigi_TaihoaSoanntengTuichiautian.csv"

    itaigi_paths = [itaigi] if itaigi.exists() else []
    taihoa_paths = [taihoa] if taihoa.exists() else []

    if not itaigi_paths and not taihoa_paths:
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
    convert_chhoetaigi(itaigi_paths, taihoa_paths, output_path, corpus_freq=corpus_freq)
    print(f"Written: {output_path}")


if __name__ == "__main__":
    main()
