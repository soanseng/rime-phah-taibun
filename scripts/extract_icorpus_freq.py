"""Extract word frequencies from iCorpus TL romanization data.

Parses the human-corrected iCorpus parallel news corpus to count
syllable and word frequencies for Rime dictionary weighting.
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import TextIO


def tokenize_tl_line(line: str) -> list[str]:
    """Tokenize a TL romanization line into words.

    Keeps hyphenated compounds as single tokens.
    Strips punctuation and skips non-TL tokens.

    Args:
        line: A line of TL romanization text

    Returns:
        List of TL word tokens
    """
    if not line.strip():
        return []
    raw_tokens = line.strip().split()
    tokens = []
    for token in raw_tokens:
        # Strip punctuation from edges
        cleaned = re.sub(r"^[^a-zA-Z]+|[^a-zA-Z0-9\-]+$", "", token)
        if not cleaned:
            continue
        # A valid TL token should contain at least one tone number (1-9)
        # or be a known particle
        if re.search(r"[1-9]", cleaned) or cleaned.lower() in {"a", "e", "i", "o", "u", "m", "ng"}:
            tokens.append(cleaned)
    return tokens


def count_frequencies(corpus_file: TextIO) -> Counter:
    """Count word frequencies from a TL corpus file.

    Args:
        corpus_file: File-like object with one TL sentence per line

    Returns:
        Counter mapping TL words to occurrence counts
    """
    freq: Counter[str] = Counter()
    for line in corpus_file:
        tokens = tokenize_tl_line(line)
        freq.update(tokens)
    return freq


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
    """CLI entry point for iCorpus frequency extraction."""
    parser = argparse.ArgumentParser(description="Extract word frequencies from iCorpus TL data")
    parser.add_argument("--input", type=Path, required=True, help="Path to iCorpus TL text file")
    parser.add_argument("--output", type=Path, required=True, help="Output TSV path")
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"Error: Input not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.input, encoding="utf-8") as f:
        freq = count_frequencies(f)
    write_frequency_table(freq, args.output)
    print(f"Extracted {len(freq)} unique words, {sum(freq.values())} total tokens")


if __name__ == "__main__":
    main()
