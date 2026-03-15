"""Extract word frequencies from 常用900例句 (900 common Taiwanese example sentences).

Parses minnan900.json which contains 896 vocabulary terms with TL romanization
(Unicode diacritics) and example sentences. Converts Unicode TL to numeric TL
for frequency matching with the main dictionary pipeline.
"""

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

try:
    from scripts.extract_icorpus_freq import tokenize_tl_line
except ModuleNotFoundError:
    from extract_icorpus_freq import tokenize_tl_line


# Combining diacritical marks → tone numbers (same for TL and POJ)
_DIACRITIC_TO_TONE = {
    "\u0301": "2",  # acute accent → tone 2
    "\u0300": "3",  # grave accent → tone 3
    "\u0302": "5",  # circumflex → tone 5
    "\u0304": "7",  # macron → tone 7
    "\u030D": "8",  # vertical line above → tone 8
}


def unicode_tl_to_numeric(text: str) -> str:
    """Convert Unicode TL diacritics to numeric tone format.

    Processes each syllable (hyphen- or space-separated) individually:
    finds the tone diacritic, removes it, and appends the tone number
    at the end of the syllable.

    Examples:
        tsi̍t → tsit8
        lâng → lang5
        kan-na → kan1-na1
        Guá → gua2

    Args:
        text: TL text with Unicode tone diacritics

    Returns:
        TL text with numeric tones appended to each syllable
    """
    if not text:
        return text

    result = text.lower()

    # Process each token (space-separated)
    tokens = result.split()
    converted_tokens = []
    for token in tokens:
        # Process each syllable (hyphen-separated within a token)
        syllables = token.split("-")
        converted_syllables = []
        for syl in syllables:
            converted_syllables.append(_convert_syllable(syl))
        converted_tokens.append("-".join(converted_syllables))

    return " ".join(converted_tokens)


def _convert_syllable(syllable: str) -> str:
    """Convert a single TL syllable from Unicode diacritics to numeric tone.

    Args:
        syllable: A single TL syllable like 'lâng' or 'tsi̍t'

    Returns:
        Syllable with numeric tone like 'lang5' or 'tsit8'
    """
    # Strip punctuation from edges
    prefix = ""
    suffix = ""
    core = syllable
    while core and not core[0].isalpha() and core[0] not in "\u0300\u0301\u0302\u0304\u030D":
        prefix += core[0]
        core = core[1:]
    while core and not core[-1].isalpha() and core[-1] not in "\u0300\u0301\u0302\u0304\u030D":
        suffix = core[-1] + suffix
        core = core[:-1]

    if not core:
        return syllable

    # NFD decompose to separate combining marks
    decomposed = unicodedata.normalize("NFD", core)

    tone = ""
    chars = []
    for ch in decomposed:
        if ch in _DIACRITIC_TO_TONE:
            tone = _DIACRITIC_TO_TONE[ch]
        else:
            chars.append(ch)

    # NFC compose back
    base = unicodedata.normalize("NFC", "".join(chars))

    # If no diacritic found, assume tone 1
    if not tone:
        tone = "1"

    return prefix + base + tone + suffix


def extract_900leku_sentences(json_path: Path) -> tuple[list[str], Counter]:
    """Extract tokenized sentences and word frequencies from 900例句.

    Extracts both vocabulary terms (詞條臺羅) and example sentences (例句臺羅),
    converts Unicode TL to numeric TL, then tokenizes.

    Args:
        json_path: Path to minnan900.json

    Returns:
        Tuple of (list of tokenized sentence strings, word frequency Counter)
    """
    freq: Counter[str] = Counter()
    sentences: list[str] = []

    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"Error: Failed to parse {json_path}: {e}", file=sys.stderr)
        return sentences, freq

    if not isinstance(data, dict):
        print(f"Error: Expected JSON object, got {type(data).__name__}", file=sys.stderr)
        return sentences, freq

    for _key, entry in data.items():
        if not isinstance(entry, dict):
            continue

        # Process vocabulary term TL
        term_tl = entry.get("詞條臺羅", "")
        if term_tl:
            numeric_tl = unicode_tl_to_numeric(term_tl)
            tokens = tokenize_tl_line(numeric_tl)
            if tokens:
                freq.update(tokens)

        # Process example sentence TL
        sentence_tl = entry.get("例句臺羅", "")
        if sentence_tl:
            numeric_tl = unicode_tl_to_numeric(sentence_tl)
            tokens = tokenize_tl_line(numeric_tl)
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
    """CLI entry point for 900例句 frequency extraction."""
    parser = argparse.ArgumentParser(
        description="Extract word frequencies from 常用900例句"
    )
    parser.add_argument(
        "--input", type=Path, required=True, help="Path to minnan900.json"
    )
    parser.add_argument("--output", type=Path, required=True, help="Output frequency TSV path")
    parser.add_argument("--sentences", type=Path, help="Output tokenized sentences file")
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"Error: Input not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    sentences, freq = extract_900leku_sentences(args.input)

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
