"""Build reverse lookup dictionary: Mandarin → Taiwanese.

Creates a Rime-compatible reverse dictionary that allows users to input
Mandarin Chinese and look up Taiwanese pronunciations and Han-Lo writing.
"""

import argparse
import sys
from pathlib import Path


def build_reverse_entries(entries: list[dict]) -> list[dict]:
    """Build reverse lookup entries from forward dictionary entries.

    Args:
        entries: List of forward dict entries with hoabun, hanlo, kip_input fields

    Returns:
        List of reverse entries with hoabun as lookup key
    """
    result = []
    for entry in entries:
        hoabun = entry.get("hoabun", "").strip()
        if not hoabun:
            continue
        result.append(
            {
                "hoabun": hoabun,
                "hanlo": entry["hanlo"],
                "kip_input": entry["kip_input"],
            }
        )
    return result


def write_reverse_dict(entries: list[dict], output_path: Path) -> None:
    """Write reverse lookup entries to Rime dict.yaml format.

    Each entry maps a Mandarin word to its Taiwanese Han-Lo form,
    with the Taiwanese pronunciation shown in the comment field.

    Args:
        entries: List of reverse lookup entries
        output_path: Path to write the reverse dict.yaml
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write("name: phah_taibun_reverse\n")
        f.write('version: "0.1.0"\n')
        f.write("sort: by_weight\n")
        f.write("use_preset_vocabulary: false\n")
        f.write("...\n")
        for entry in entries:
            hanlo = entry["hanlo"]
            hoabun = entry["hoabun"]
            f.write(f"{hanlo}\t{hoabun}\t500\n")


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for reverse dictionary builder."""
    parser = argparse.ArgumentParser(description="Build reverse lookup dictionary")
    parser.add_argument("--input", type=Path, required=True, help="Path to ChhoeTaigiDatabase directory")
    parser.add_argument("--output", type=Path, required=True, help="Output path for reverse dict.yaml")
    args = parser.parse_args(argv)

    try:
        from scripts.convert_chhoetaigi import parse_itaigi_csv, parse_taihoa_csv
    except ModuleNotFoundError:
        from convert_chhoetaigi import parse_itaigi_csv, parse_taihoa_csv

    data_dir = args.input / "ChhoeTaigiDatabase"
    if not data_dir.exists():
        data_dir = args.input

    all_entries: list[dict] = []
    itaigi = data_dir / "ChhoeTaigi_iTaigiHoataiTuichiautian.csv"
    if itaigi.exists():
        with open(itaigi, encoding="utf-8-sig") as f:
            all_entries.extend(parse_itaigi_csv(f))
    taihoa = data_dir / "ChhoeTaigi_TaihoaSoanntengTuichiautian.csv"
    if taihoa.exists():
        with open(taihoa, encoding="utf-8-sig") as f:
            all_entries.extend(parse_taihoa_csv(f))

    if not all_entries:
        print(f"Error: No CSV files found in {data_dir}", file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    reverse = build_reverse_entries(all_entries)
    write_reverse_dict(reverse, args.output)
    print(f"Written {len(reverse)} reverse entries to {args.output}")


if __name__ == "__main__":
    main()
