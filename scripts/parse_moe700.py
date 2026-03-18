"""Parse MOE 700字台語漢字推薦用字 CSV into moe700.yaml.

Extracts the 建議用字 column from 700iongji.csv and writes a simple
YAML list for the Lua runtime to load.
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import TextIO

import yaml


def parse_moe700_csv(csvfile: TextIO) -> list[str]:
    """Parse 700iongji.csv and extract recommended words.

    Args:
        csvfile: File-like object containing the MOE 700 CSV

    Returns:
        List of recommended words (建議用字)
    """
    words = []
    reader = csv.DictReader(csvfile)
    for row in reader:
        word = row.get("建議用字", "").strip()
        if word:
            words.append(word)
    return words


def write_moe700_yaml(words: list[str], output_path: Path) -> None:
    """Write recommended word list to YAML.

    Args:
        words: List of recommended words
        output_path: Path to write moe700.yaml
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# 教育部推薦700字台語漢字\n")
        f.write("# Source: https://github.com/yiufung/minnan-700/blob/master/700iongji.csv\n\n")
        yaml.dump(words, f, allow_unicode=True, default_flow_style=False)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Parse MOE 700字 CSV to moe700.yaml")
    parser.add_argument("--input", type=Path, required=True, help="Path to 700iongji.csv")
    parser.add_argument("--output", type=Path, required=True, help="Output path for moe700.yaml")
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.input, encoding="utf-8") as f:
        words = parse_moe700_csv(f)
    write_moe700_yaml(words, args.output)
    print(f"Written {len(words)} words to {args.output}")


if __name__ == "__main__":
    main()
