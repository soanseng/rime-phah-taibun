"""Build reverse dictionary from KipSutianDataMirror (65K entries).

Uses the richer KipSutian CSV (教育部台語辭典鏡像) which has 2.4x more
entries than moedict-data-twblg, plus definitions, examples, and variants.
CC BY-ND 3.0 — reverse lookup only.
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import TextIO


def parse_kipsutian_csv(csvfile: TextIO) -> list[dict]:
    """Parse KipSutian kautian.csv into structured entries.

    Args:
        csvfile: File-like object for kautian.csv

    Returns:
        List of dicts with word, reading, definition, entry_type fields
    """
    entries = []
    reader = csv.DictReader(csvfile)
    for row in reader:
        word = row.get("漢字", "").strip()
        reading = row.get("羅馬字", "").strip()
        entry_type = row.get("詞目類型", "").strip()
        definition = row.get("解說", "").strip()
        if not word or not reading:
            continue
        entries.append(
            {
                "word": word,
                "reading": reading,
                "entry_type": entry_type,
                "definition": definition,
            }
        )
    return entries


def write_kipsutian_reverse_dict(entries: list[dict], output_path: Path) -> None:
    """Write KipSutian reverse dict.yaml.

    Args:
        entries: Parsed KipSutian entries
        output_path: Output path for reverse dict
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write("name: phah_taibun_reverse\n")
        f.write('version: "0.3.0"\n')
        f.write("sort: by_weight\n")
        f.write("use_preset_vocabulary: false\n")
        f.write("...\n")
        seen: set[tuple[str, str]] = set()
        for entry in entries:
            word = entry["word"]
            key = (word, word)
            if key in seen:
                continue
            seen.add(key)
            # Main entries get higher weight than variants
            weight = 500 if entry["entry_type"] == "主詞目" else 300
            f.write(f"{word}\t{word}\t{weight}\n")


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Build reverse dict from KipSutian")
    parser.add_argument("--input", type=Path, required=True, help="Path to kautian.csv")
    parser.add_argument("--output", type=Path, required=True, help="Output reverse dict.yaml")
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"Error: not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(args.input, encoding="utf-8") as f:
        entries = parse_kipsutian_csv(f)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_kipsutian_reverse_dict(entries, args.output)
    print(f"Written {len(entries)} entries to {args.output}")


if __name__ == "__main__":
    main()
