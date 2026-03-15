"""Extract word frequencies from KipSutian (教育部台語辭典鏡像) CSV data.

Reads the kautian.csv with 65K dictionary entries and extracts romanization
tokens from the 羅馬字 (main reading) and 又唸作 (alternate reading) columns,
producing word frequency counts and tokenized sentence output.
"""

import argparse
import csv
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import TextIO

try:
    from scripts.extract_icorpus_freq import tokenize_tl_line
except ModuleNotFoundError:
    from extract_icorpus_freq import tokenize_tl_line


# Columns that contain romanization data worth extracting
_READING_COLUMNS = ("羅馬字", "又唸作", "合音唸作", "俗唸作")

# TL diacritical vowels and nasal marks used in KipSutian romanization
_TL_DIACRITICAL_RE = re.compile(
    r"[\u0300-\u036f]"  # combining diacritical marks (tone marks, nasal)
    r"|[áàâāéèêēíìîīóòôōúùûū]"  # precomposed accented vowels
    r"|ⁿ"  # nasal superscript
    r"|[̍̄]",  # combining dot above right / macron
)


def tokenize_tl_diacritical(line: str) -> list[str]:
    """Tokenize a TL romanization line that uses diacritical marks.

    KipSutian uses Unicode diacritics (e.g., tsia̍h-pn̄g) rather than
    numeric tone markers. This function accepts tokens containing either
    diacritical marks or tone numbers, falling back to tokenize_tl_line
    for numbered-tone input.

    Args:
        line: A line of TL romanization text (diacritical or numbered)

    Returns:
        List of TL word tokens
    """
    if not line.strip():
        return []
    # First try the numbered-tone tokenizer
    numbered = tokenize_tl_line(line)
    if numbered:
        return numbered
    # Handle diacritical TL
    raw_tokens = line.strip().split()
    tokens = []
    for token in raw_tokens:
        # Strip leading/trailing punctuation but keep Unicode letters and hyphens
        cleaned = token.strip(".,;:!?\"'()[]{}。，、；：！？「」『』（）")
        if not cleaned:
            continue
        # Normalize to NFC for consistent matching
        cleaned = unicodedata.normalize("NFC", cleaned)
        # A valid diacritical TL token should contain Latin letters
        if not re.search(r"[a-zA-Z]", cleaned):
            continue
        # Accept if it has diacritical marks, tone numbers, or is a known particle
        has_diacritics = bool(_TL_DIACRITICAL_RE.search(unicodedata.normalize("NFD", cleaned)))
        has_tone_num = bool(re.search(r"[1-9]", cleaned))
        is_particle = cleaned.lower() in {"a", "e", "i", "o", "u", "m", "ng"}
        if has_diacritics or has_tone_num or is_particle:
            tokens.append(cleaned)
    return tokens


def extract_kipsutian_sentences(csvfile: TextIO) -> tuple[list[str], Counter]:
    """Extract romanization tokens from KipSutian CSV entries.

    Reads each row and tokenizes romanization from reading columns.
    KipSutian uses diacritical TL romanization, so this uses
    tokenize_tl_diacritical which handles both diacritical and
    numbered tone formats.

    Args:
        csvfile: File-like object for kautian.csv (utf-8 or utf-8-sig)

    Returns:
        Tuple of (list of tokenized sentence strings, word frequency Counter)
    """
    sentences: list[str] = []
    freq: Counter[str] = Counter()
    reader = csv.DictReader(csvfile)

    for row in reader:
        for col in _READING_COLUMNS:
            reading = row.get(col, "").strip()
            if not reading:
                continue
            tokens = tokenize_tl_diacritical(reading)
            if tokens:
                sentences.append(" ".join(tokens))
                freq.update(tokens)

    return sentences, freq


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for KipSutian sentence extraction."""
    parser = argparse.ArgumentParser(
        description="Extract word frequencies from KipSutian CSV"
    )
    parser.add_argument(
        "--input", type=Path, required=True, help="Path to kautian.csv"
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="Output frequency TSV path"
    )
    parser.add_argument(
        "--sentences", type=Path, help="Output tokenized sentences file"
    )
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"Error: not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(args.input, encoding="utf-8-sig") as f:
        sentences, freq = extract_kipsutian_sentences(f)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for word, count in freq.most_common():
            f.write(f"{word}\t{count}\n")
    print(f"Extracted {len(freq)} unique words, {sum(freq.values())} total tokens")

    if args.sentences:
        args.sentences.parent.mkdir(parents=True, exist_ok=True)
        with open(args.sentences, "w", encoding="utf-8") as f:
            for sent in sentences:
                f.write(sent + "\n")
        print(f"Wrote {len(sentences)} tokenized sentences")


if __name__ == "__main__":
    main()
