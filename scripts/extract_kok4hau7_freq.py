"""Extract word frequencies from 康軒 elementary school Taiwanese textbooks.

Parses the 12 JSON textbook volumes (康軒1.json to 康軒12.json) which contain
aligned Han-ji and TL romanization paragraphs, tokenizes the TL text,
and produces frequency counts and sentence lists.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

try:
    from scripts.extract_icorpus_freq import tokenize_tl_line
except ModuleNotFoundError:
    from extract_icorpus_freq import tokenize_tl_line


def extract_kok4hau7_sentences(data_dir: Path) -> tuple[list[str], Counter]:
    """Extract tokenized sentences and word frequencies from 康軒 textbooks.

    Reads JSON files from JSON格式資料/康軒/ directory. Each file contains
    lessons with paragraph pairs: [Han-ji text, TL romanization].

    Args:
        data_dir: Root directory of kok4hau7-kho3pun2 repo

    Returns:
        Tuple of (list of tokenized sentence strings, word frequency Counter)
    """
    freq: Counter[str] = Counter()
    sentences: list[str] = []

    json_dir = data_dir / "JSON格式資料" / "康軒"
    if not json_dir.exists():
        # Try alternative paths
        for candidate in [data_dir / "JSON格式資料", data_dir]:
            json_files = sorted(candidate.glob("康軒*.json"))
            if json_files:
                json_dir = candidate
                break

    json_files = sorted(json_dir.glob("康軒*.json"))
    if not json_files:
        print(f"Warning: No 康軒*.json files found in {json_dir}", file=sys.stderr)
        return sentences, freq

    for json_file in json_files:
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            print(f"Warning: Failed to parse {json_file}", file=sys.stderr)
            continue

        # Structure: {"資料": [{"篇名": "...", "段": [["漢字", "羅馬字"], ...]}, ...]}
        lessons = data.get("資料", [])
        if not isinstance(lessons, list):
            continue

        for lesson in lessons:
            if not isinstance(lesson, dict):
                continue
            paragraphs = lesson.get("段", [])
            if not isinstance(paragraphs, list):
                continue
            for para in paragraphs:
                if not isinstance(para, list) or len(para) < 2:
                    continue
                # para[1] is the TL romanization with numeric tones
                tl_text = para[1]
                if not isinstance(tl_text, str) or not tl_text.strip():
                    continue
                # Split into lines and tokenize each
                for line in tl_text.splitlines():
                    tokens = tokenize_tl_line(line)
                    if tokens:
                        sentences.append(" ".join(tokens))
                        freq.update(tokens)

    return sentences, freq


def write_frequency_table(freq: Counter, output_path: Path) -> None:
    """Write frequency data to a TSV file sorted by count descending."""
    with open(output_path, "w", encoding="utf-8") as f:
        for word, count in freq.most_common():
            f.write(f"{word}\t{count}\n")


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for 康軒 textbook frequency extraction."""
    parser = argparse.ArgumentParser(
        description="Extract word frequencies from 康軒 elementary school Taiwanese textbooks"
    )
    parser.add_argument(
        "--input", type=Path, required=True, help="Directory containing kok4hau7-kho3pun2 data"
    )
    parser.add_argument("--output", type=Path, required=True, help="Output frequency TSV path")
    parser.add_argument("--sentences", type=Path, help="Output tokenized sentences file")
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"Error: Input not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    sentences, freq = extract_kok4hau7_sentences(args.input)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_frequency_table(freq, args.output)
    print(f"Extracted {len(freq)} unique words, {sum(freq.values())} total tokens")

    if args.sentences:
        args.sentences.parent.mkdir(parents=True, exist_ok=True)
        with open(args.sentences, "w", encoding="utf-8") as f:
            for sent in sentences:
                f.write(sent + "\n")
        print(f"Wrote {len(sentences)} tokenized sentences")


if __name__ == "__main__":
    main()
