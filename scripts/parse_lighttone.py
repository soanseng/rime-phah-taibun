"""Parse khin1siann1-hun1sik4 light-tone (輕聲) rules.

Extracts tone sandhi handling rules for light-tone words:
- 分寫 (separate): word boundary before this morpheme
- 連寫 (connect): attach directly to preceding word
- 補語 (complement): grammatical complement attachment
- 不處理 (no action): no special handling
"""

import csv
from pathlib import Path
from typing import TextIO


def parse_lighttone_csv(csvfile: TextIO) -> list[dict]:
    """Parse light-tone rules CSV.

    Args:
        csvfile: File-like object for the CSV

    Returns:
        List of dicts with tl, hanzi, rule fields
    """
    rules = []
    reader = csv.DictReader(csvfile)
    for row in reader:
        tl = row.get("臺羅", "").strip()
        hanzi = row.get("漢字", "").strip()
        rule = row.get("分連不處理", "").strip()
        if not tl:
            continue
        rules.append(
            {
                "tl": tl,
                "hanzi": hanzi,
                "rule": rule,
            }
        )
    return rules


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(description="Parse light-tone rules")
    parser.add_argument("--input", type=Path, required=True, help="Path to light-tone CSV")
    parser.add_argument("--output", type=Path, required=True, help="Output JSON path")
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"Error: not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(args.input, encoding="utf-8") as f:
        rules = parse_lighttone_csv(f)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)
    print(f"Parsed {len(rules)} light-tone rules to {args.output}")


if __name__ == "__main__":
    main()
