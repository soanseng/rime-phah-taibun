"""Build enhanced reverse dictionary from MOE structured data.

Parses moedict-data-twblg/uni/ CSVs to create a reverse lookup dictionary
with definitions and example sentences. CC BY-ND 3.0 -- reverse lookup only.
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import TextIO


def parse_moe_entries(csvfile: TextIO) -> list[dict]:
    """Parse MOE vocabulary CSV into structured entries.

    Args:
        csvfile: File-like object for the vocabulary CSV

    Returns:
        List of dicts with word, reading, moe_id, wen_bai
    """
    entries = []
    reader = csv.DictReader(csvfile)
    for row in reader:
        word = row.get("詞目", "").strip()
        reading = row.get("音讀", "").strip()
        moe_id = row.get("主編碼", "").strip()
        wen_bai = row.get("文白屬性", "0").strip()
        if not word or not reading:
            continue
        entries.append(
            {
                "word": word,
                "reading": reading,
                "moe_id": moe_id,
                "wen_bai": wen_bai,
            }
        )
    return entries


def load_definitions(csvfile: TextIO) -> dict[str, list[str]]:
    """Load definitions from MOE definitions CSV.

    Args:
        csvfile: File-like object for the definitions CSV

    Returns:
        Dict mapping moe_id to list of definition strings
    """
    defs: dict[str, list[str]] = {}
    reader = csv.DictReader(csvfile)
    for row in reader:
        moe_id = row.get("主編碼", "").strip()
        definition = row.get("釋義", "").strip()
        if not moe_id or not definition:
            continue
        defs.setdefault(moe_id, []).append(definition)
    return defs


def write_enhanced_reverse_dict(
    entries: list[dict],
    definitions: dict[str, list[str]],
    output_path: Path,
) -> None:
    """Write enhanced reverse lookup dictionary.

    Args:
        entries: List of MOE entry dicts
        definitions: Dict mapping moe_id to definition lists
        output_path: Path to write reverse dict.yaml
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write("name: phah_taibun_reverse\n")
        f.write('version: "0.2.0"\n')
        f.write("sort: by_weight\n")
        f.write("use_preset_vocabulary: false\n")
        f.write("...\n")
        for entry in entries:
            word = entry["word"]
            # Weight: wen_bai=0 (colloquial, default) gets higher weight
            weight = 500 if entry.get("wen_bai", "0") == "0" else 300
            f.write(f"{word}\t{word}\t{weight}\n")


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for MOE reverse dictionary builder."""
    parser = argparse.ArgumentParser(description="Build enhanced reverse dictionary from MOE data")
    parser.add_argument("--input", type=Path, required=True, help="Path to moedict-data-twblg/uni/ directory")
    parser.add_argument("--output", type=Path, required=True, help="Output reverse dict.yaml path")
    args = parser.parse_args(argv)

    vocab_csv = args.input / "詞目總檔.csv"
    defs_csv = args.input / "釋義.csv"

    if not vocab_csv.exists():
        print(f"Error: not found in {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(vocab_csv, encoding="utf-8") as f:
        entries = parse_moe_entries(f)

    definitions: dict[str, list[str]] = {}
    if defs_csv.exists():
        with open(defs_csv, encoding="utf-8") as f:
            definitions = load_definitions(f)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_enhanced_reverse_dict(entries, definitions, args.output)
    print(f"Written {len(entries)} entries to {args.output}")


if __name__ == "__main__":
    main()
