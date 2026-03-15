"""Extract word frequencies from Khin-hoan POJ (白話字) text corpus.

Reads plain-text POJ romanization files, converts them to TL using
poj_to_tl(), tokenizes, and produces frequency counts and sentence lists.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

try:
    from scripts.tl_poj_convert import poj_to_tl
    from scripts.extract_icorpus_freq import tokenize_tl_line
except ModuleNotFoundError:
    from tl_poj_convert import poj_to_tl
    from extract_icorpus_freq import tokenize_tl_line


def extract_pojbh_sentences(data_dir: Path) -> tuple[list[str], Counter]:
    """Extract tokenized sentences and word frequencies from POJ corpus.

    Tries pojbh.json first (structured JSON with tailo field containing POJ lines),
    then falls back to reading .txt files recursively.

    Args:
        data_dir: Directory containing POJ corpus data

    Returns:
        Tuple of (list of space-joined tokenized sentences, word frequency Counter)
    """
    freq: Counter[str] = Counter()
    sentences: list[str] = []

    # Try pojbh.json first
    json_path = data_dir / "pojbh.json"
    if json_path.exists():
        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                for record in data:
                    if not isinstance(record, dict):
                        continue
                    tailo = record.get("tailo", [])
                    if not isinstance(tailo, list):
                        continue
                    for line in tailo:
                        if not isinstance(line, str) or not line.strip():
                            continue
                        tl_line = poj_to_tl(line)
                        tokens = tokenize_tl_line(tl_line)
                        if tokens:
                            sentences.append(" ".join(tokens))
                            freq.update(tokens)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        if sentences:
            return sentences, freq

    # Fallback: .txt files
    txt_files = sorted(data_dir.rglob("*.txt"))
    for txt_file in txt_files:
        try:
            text = txt_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line in text.splitlines():
            tl_line = poj_to_tl(line)
            tokens = tokenize_tl_line(tl_line)
            if tokens:
                sentences.append(" ".join(tokens))
                freq.update(tokens)

    return sentences, freq


def write_frequency_table(freq: Counter, output_path: Path) -> None:
    """Write frequency data to a TSV file sorted by count descending.

    Args:
        freq: Counter mapping words to counts
        output_path: Path to write TSV
    """
    with open(output_path, "w", encoding="utf-8") as f:
        for word, count in freq.most_common():
            f.write(f"{word}\t{count}\n")


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for Khin-hoan POJ frequency extraction."""
    parser = argparse.ArgumentParser(
        description="Extract word frequencies from Khin-hoan POJ text corpus"
    )
    parser.add_argument(
        "--input", type=Path, required=True, help="Directory containing POJ .txt files"
    )
    parser.add_argument("--output", type=Path, required=True, help="Output frequency TSV path")
    parser.add_argument("--sentences", type=Path, help="Output tokenized sentences file")
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"Error: Input not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    sentences, freq = extract_pojbh_sentences(args.input)

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
