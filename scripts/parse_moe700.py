"""Parse MOE 700字 + 常用900例句 recommended words into moe700.yaml.

Extracts the 建議用字 column from 700iongji.csv and, when --leku900 is
given, the 詞條漢字 terms from minnan900.json. The Lua runtime loads
the merged list (phah_taibun_recommend.lua) and gives every entry the
same ◆ badge and moe nudge tier — a word present in several sources is
deduplicated here so boosts never stack (the lua side additionally
picks one tier per candidate via if/elseif).
"""

import argparse
import csv
import json
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


def parse_leku900_json(path: Path) -> list[str]:
    """Extract 詞條漢字 terms from the 常用900例句 corpus JSON.

    Args:
        path: Path to minnan900.json (dict or list of entries)

    Returns:
        List of vocabulary terms, in corpus order
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.values() if isinstance(data, dict) else data
    words = []
    for entry in entries:
        word = (entry.get("詞條漢字") or "").strip()
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
        f.write("# 推薦用字: 教育部推薦700字台語漢字 + 常用900例句詞條\n")
        f.write("# Sources: https://github.com/yiufung/minnan-700/blob/master/700iongji.csv\n")
        f.write("#          https://github.com/Taiwanese-Corpus/Sin1pak8tshi7_2015_900-le7ku3\n\n")
        yaml.dump(words, f, allow_unicode=True, default_flow_style=False)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Parse MOE 700字 CSV (+900例句) to moe700.yaml")
    parser.add_argument("--input", type=Path, required=True, help="Path to 700iongji.csv")
    parser.add_argument("--leku900", type=Path, default=None, help="Optional minnan900.json to merge")
    parser.add_argument("--output", type=Path, required=True, help="Output path for moe700.yaml")
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    if args.leku900 is not None and not args.leku900.exists():
        print(f"Error: 900例句 file not found: {args.leku900}", file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.input, encoding="utf-8") as f:
        words = parse_moe700_csv(f)

    merged = len(words)
    if args.leku900 is not None:
        seen = set(words)
        for word in parse_leku900_json(args.leku900):
            if word not in seen:
                seen.add(word)
                words.append(word)

    write_moe700_yaml(words, args.output)
    extra = f" (+{len(words) - merged} from 900例句)" if args.leku900 is not None else ""
    print(f"Written {len(words)} words to {args.output}{extra}")


if __name__ == "__main__":
    main()
