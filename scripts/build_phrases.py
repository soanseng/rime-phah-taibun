"""Phrase builder: reverse index, bigram extraction, and dictionary entry generation.

Extracts high-frequency bigrams from sentence corpora and generates new
dictionary entries by looking up constituent words in a Rime dict.
"""

import argparse
import re
import sys
from collections import Counter
from math import log10
from pathlib import Path

# YAML header lines to skip when parsing dict data
_YAML_HEADER_PREFIXES = ("---", "name:", "version:", "sort:", "use_preset_vocabulary:", "...")


def _strip_tones(text: str) -> str:
    """Strip tone numbers (1-9) from romanization.

    Examples:
        gua2 → gua
        tsiah8-png7 → tsiah-png
    """
    return re.sub(r"[1-9]", "", text)


def build_reverse_index(dict_lines: list[str]) -> dict[str, list[dict]]:
    """Build rime_key → [{text, weight}] mapping from dict.yaml data lines.

    Args:
        dict_lines: Lines in format ``text\\trime_key\\tweight``.
            YAML header lines (starting with ``---``, ``name:``, etc.) are skipped.

    Returns:
        Dict mapping each rime_key to a list of {text, weight} dicts,
        sorted by weight descending.
    """
    index: dict[str, list[dict]] = {}
    for line in dict_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.startswith(p) for p in _YAML_HEADER_PREFIXES):
            continue
        parts = stripped.split("\t")
        if len(parts) < 3:
            continue
        text, rime_key, weight_str = parts[0], parts[1], parts[2]
        try:
            weight = int(weight_str)
        except ValueError:
            continue
        index.setdefault(rime_key, []).append({"text": text, "weight": weight})

    # Sort each list by weight descending
    for key in index:
        index[key].sort(key=lambda d: d["weight"], reverse=True)

    return index


def extract_bigrams(sentences: list[str], min_count: int = 1) -> Counter:
    """Extract bigram frequencies from tokenized sentences.

    Args:
        sentences: List of space-separated token strings (with tone numbers).
        min_count: Minimum count threshold (kept for API, filtering done elsewhere).

    Returns:
        Counter mapping ``(word1, word2)`` tuples (tone-stripped) to counts.
    """
    bigrams: Counter = Counter()
    for sentence in sentences:
        tokens = sentence.strip().split()
        stripped = [_strip_tones(t) for t in tokens]
        for i in range(len(stripped) - 1):
            if stripped[i] and stripped[i + 1]:
                bigrams[(stripped[i], stripped[i + 1])] += 1
    return bigrams


def generate_phrase_entries(
    bigrams: Counter,
    reverse_index: dict[str, list[dict]],
    existing_keys: set[tuple[str, str]],
    min_count: int = 5,
    base_weight: int = 500,
) -> list[dict]:
    """Generate new dictionary entries from high-frequency bigrams.

    Args:
        bigrams: Counter of ``(word1, word2)`` → count.
        reverse_index: rime_key → [{text, weight}] mapping.
        existing_keys: Set of ``(hanlo, rime_key)`` already in the dictionary.
        min_count: Minimum bigram count to qualify.
        base_weight: Base weight for generated entries.

    Returns:
        List of dicts with ``hanlo``, ``rime_key``, ``weight`` keys.
    """
    entries = []
    for (w1, w2), count in bigrams.items():
        if count < min_count:
            continue
        if w1 not in reverse_index or w2 not in reverse_index:
            continue
        text1 = reverse_index[w1][0]["text"]
        text2 = reverse_index[w2][0]["text"]
        hanlo = text1 + text2
        rime_key = f"{w1} {w2}"
        if (hanlo, rime_key) in existing_keys:
            continue
        weight = int(base_weight * (1.0 + log10(1 + count) * 0.3))
        entries.append({"hanlo": hanlo, "rime_key": rime_key, "weight": weight})
    return entries


def build_phrases_from_files(
    dict_path: Path,
    sentence_paths: list[Path],
    output_path: Path,
    min_count: int = 5,
) -> int:
    """End-to-end phrase building from dict and sentence files.

    Args:
        dict_path: Path to Rime dict.yaml file.
        sentence_paths: Paths to sentence files (one sentence per line).
        output_path: Path to write generated entries.
        min_count: Minimum bigram count to qualify.

    Returns:
        Number of new entries written.
    """
    # Load dict and skip YAML header
    raw_lines = Path(dict_path).read_text(encoding="utf-8").splitlines()
    # Find the end of YAML header (line with '...')
    data_start = 0
    for i, line in enumerate(raw_lines):
        if line.strip() == "...":
            data_start = i + 1
            break
    data_lines = raw_lines[data_start:]

    # Build reverse index
    reverse_index = build_reverse_index(data_lines)

    # Collect existing (hanlo, rime_key) pairs
    existing_keys: set[tuple[str, str]] = set()
    for line in data_lines:
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split("\t")
        if len(parts) >= 2:
            existing_keys.add((parts[0], parts[1]))

    # Read all sentences
    all_sentences: list[str] = []
    for sp in sentence_paths:
        text = Path(sp).read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if line:
                all_sentences.append(line)

    # Extract bigrams and generate entries
    bigrams = extract_bigrams(all_sentences)
    entries = generate_phrase_entries(bigrams, reverse_index, existing_keys, min_count=min_count)

    # Write output
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(f"{entry['hanlo']}\t{entry['rime_key']}\t{entry['weight']}\n")

    return len(entries)


def main():
    """CLI entry point for phrase builder."""
    parser = argparse.ArgumentParser(description="Build phrase entries from bigram extraction")
    parser.add_argument("--dict", type=Path, required=True, help="Path to Rime dict.yaml")
    parser.add_argument("--sentences", type=Path, nargs="+", required=True, help="Sentence file(s)")
    parser.add_argument("--output", type=Path, required=True, help="Output path for generated entries")
    parser.add_argument("--min-count", type=int, default=5, help="Minimum bigram count (default: 5)")
    args = parser.parse_args()

    count = build_phrases_from_files(
        dict_path=args.dict,
        sentence_paths=args.sentences,
        output_path=args.output,
        min_count=args.min_count,
    )
    print(f"Generated {count} phrase entries → {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
