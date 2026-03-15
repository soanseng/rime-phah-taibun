"""Extract word frequencies from NMTL 2006 literary corpus.

Parses the nmtl_2006_dadwt corpus (2,169 Taiwanese literary works) to count
TL word frequencies. Supports both JSON format (nmtl.json with aligned
Han-Lo/TL pairs) and plain text fallback (.tbk/.txt files).
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


def extract_nmtl_sentences(data_dir: Path) -> tuple[list[str], Counter]:
    """Extract tokenized sentences and word frequencies from NMTL corpus.

    Tries nmtl.json first (structured JSON with Han-Lo and TL pairs).
    Falls back to reading all .tbk and .txt files recursively.

    Args:
        data_dir: Directory containing NMTL corpus data

    Returns:
        Tuple of (list of tokenized sentence strings, word frequency Counter)
    """
    sentences: list[str] = []
    freq: Counter[str] = Counter()

    json_path = data_dir / "nmtl.json"
    if json_path.exists():
        _extract_from_json(json_path, sentences, freq)
    else:
        _extract_from_text_files(data_dir, sentences, freq)

    return sentences, freq


def _extract_from_json(
    json_path: Path,
    sentences: list[str],
    freq: Counter,
) -> None:
    """Extract sentences from nmtl.json format.

    Actual structure: [{"資料": [["hanlo_text", "romanization_text"], ...], ...}, ...]
    Each entry in 資料 is a pair: [Han-Lo text, POJ/TL romanization].
    """
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return

    if not isinstance(data, list):
        return

    for record in data:
        if not isinstance(record, dict):
            continue
        paragraphs = record.get("資料", [])
        if not isinstance(paragraphs, list):
            continue
        for paragraph in paragraphs:
            if not isinstance(paragraph, list) or len(paragraph) < 2:
                continue
            tl_line = paragraph[1]  # second element is romanization
            if not isinstance(tl_line, str) or not tl_line.strip():
                continue
            tokens = tokenize_tl_line(tl_line)
            if tokens:
                sentences.append(" ".join(tokens))
                freq.update(tokens)


def _extract_from_text_files(
    data_dir: Path,
    sentences: list[str],
    freq: Counter,
) -> None:
    """Fallback: extract from .tbk and .txt files recursively."""
    text_files = sorted(
        list(data_dir.rglob("*.tbk")) + list(data_dir.rglob("*.txt"))
    )
    for text_file in text_files:
        try:
            with open(text_file, encoding="utf-8") as f:
                for line in f:
                    tokens = tokenize_tl_line(line)
                    if tokens:
                        sentences.append(" ".join(tokens))
                        freq.update(tokens)
        except UnicodeDecodeError:
            continue


def write_nmtl_output(
    data_dir: Path,
    freq_path: Path,
    sentences_path: Path | None,
) -> None:
    """Write frequency TSV and optionally a sentences file.

    Args:
        data_dir: Directory containing NMTL corpus data
        freq_path: Output path for frequency TSV
        sentences_path: Output path for tokenized sentences (or None to skip)
    """
    sentences, freq = extract_nmtl_sentences(data_dir)

    freq_path.parent.mkdir(parents=True, exist_ok=True)
    with open(freq_path, "w", encoding="utf-8") as f:
        for word, count in freq.most_common():
            f.write(f"{word}\t{count}\n")

    if sentences_path is not None:
        sentences_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sentences_path, "w", encoding="utf-8") as f:
            for sentence in sentences:
                f.write(sentence + "\n")


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for NMTL frequency extraction."""
    parser = argparse.ArgumentParser(
        description="Extract word frequencies from NMTL literary corpus"
    )
    parser.add_argument(
        "--input", type=Path, required=True, help="Path to nmtl_2006_dadwt directory"
    )
    parser.add_argument("--output", type=Path, required=True, help="Output TSV path")
    parser.add_argument(
        "--sentences", type=Path, default=None, help="Output tokenized sentences file"
    )
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"Error: Input not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    write_nmtl_output(args.input, args.output, args.sentences)

    # Read back for summary
    sentences, freq = extract_nmtl_sentences(args.input)
    print(f"Extracted {len(freq)} unique words, {sum(freq.values())} total tokens")
    if args.sentences:
        print(f"Wrote {len(sentences)} sentences to {args.sentences}")


if __name__ == "__main__":
    main()
