"""Extract word frequencies from Ungian_2009 literary corpus.

Parses 1,093 JSON files from the Ungian_2009_KIPsupin corpus to count
KIP (教育部台語羅馬字) word frequencies from Taiwanese literary works.
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path


def parse_ungian_json(data: dict) -> list[str]:
    """Extract KIP romanization lines from an Ungian JSON structure.

    Args:
        data: Parsed JSON dict with 資料[].段[][] structure

    Returns:
        List of KIP romanization strings
    """
    lines = []
    for section in data.get("資料", []):
        for paragraph in section.get("段", []):
            # Each paragraph is a list: [hanlo_text, kip_text] or just [hanlo_text]
            if isinstance(paragraph, list) and len(paragraph) >= 2:
                kip_line = paragraph[1]
                if isinstance(kip_line, str) and kip_line.strip():
                    lines.append(kip_line.strip())
    return lines


def extract_kip_tokens(kip_line: str) -> list[str]:
    """Tokenize a KIP romanization line into words.

    Args:
        kip_line: A line of KIP romanization text

    Returns:
        List of KIP word tokens (keeps hyphenated compounds)
    """
    if not kip_line.strip():
        return []
    raw_tokens = kip_line.strip().split()
    tokens = []
    for token in raw_tokens:
        # Strip punctuation from edges
        cleaned = re.sub(r"^[^a-zA-Z]+|[^a-zA-Z0-9\-]+$", "", token)
        if not cleaned:
            continue
        # Keep tokens with tone numbers or known particles
        if re.search(r"[1-9]", cleaned) or cleaned.lower() in {"a", "e", "i", "o", "u", "m", "ng"}:
            tokens.append(cleaned)
    return tokens


def count_ungian_frequencies(json_dir: Path) -> Counter:
    """Count word frequencies from all JSON files in a directory tree.

    Args:
        json_dir: Root directory containing Ungian JSON files

    Returns:
        Counter mapping KIP words to occurrence counts
    """
    freq: Counter[str] = Counter()
    for json_file in sorted(json_dir.rglob("*.json")):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        for kip_line in parse_ungian_json(data):
            tokens = extract_kip_tokens(kip_line)
            freq.update(tokens)
    return freq


def write_ungian_sentences(json_dir: Path, output_path: Path) -> int:
    """Write tokenized KIP sentences from Ungian JSON files.

    Args:
        json_dir: Root directory containing Ungian JSON files
        output_path: Output file path for sentences (one per line)

    Returns:
        Count of sentences written
    """
    count = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as out:
        for json_file in sorted(json_dir.rglob("*.json")):
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            for kip_line in parse_ungian_json(data):
                tokens = extract_kip_tokens(kip_line)
                if tokens:
                    out.write(" ".join(tokens) + "\n")
                    count += 1
    return count


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for Ungian frequency extraction."""
    parser = argparse.ArgumentParser(description="Extract word frequencies from Ungian literary corpus")
    parser.add_argument("--input", type=Path, required=True, help="Path to Ungian_2009_KIPsupin directory")
    parser.add_argument("--output", type=Path, required=True, help="Output TSV path")
    parser.add_argument("--sentences", type=Path, default=None, help="Output tokenized sentences file")
    args = parser.parse_args(argv)

    json_dir = args.input / "JSON格式資料"
    if not json_dir.exists():
        json_dir = args.input

    freq = count_ungian_frequencies(json_dir)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for word, count in freq.most_common():
            f.write(f"{word}\t{count}\n")

    print(f"Extracted {len(freq)} unique words, {sum(freq.values())} total tokens")

    if args.sentences:
        sent_count = write_ungian_sentences(json_dir, args.sentences)
        print(f"Wrote {sent_count} sentences to {args.sentences}")


if __name__ == "__main__":
    main()
