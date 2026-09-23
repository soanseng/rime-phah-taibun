"""Generate phah_taibun.wordlist for whole-sentence romanization.

The Lua layer segments sentence candidates into words for 全羅 output
(word spaces between words, hyphens inside). Multi-syllable Memory
dict_lookup and phrase-level reverse lookup are not functional on
current librime-lua, so the build pipeline ships a compact word→codes
table ("word\tcode|code...") that Lua loads lazily as one string.
"""

import argparse
import re
from pathlib import Path

_CJK_ONLY = re.compile(r"^[\u3400-\u9fff]+$")


def generate_wordlist(dict_path: Path, output_path: Path) -> int:
    """Extract multi-syllable pure-CJK words from a dict.yaml.

    Args:
        dict_path: Assembled phah_taibun.dict.yaml
        output_path: Destination wordlist file

    Returns:
        Number of unique words written
    """
    words: dict[str, set[str]] = {}
    in_header = True
    for line in dict_path.read_text(encoding="utf-8").splitlines():
        if in_header:
            if line.strip() == "...":
                in_header = False
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        word, code = parts[0], parts[1]
        if "--" in word:
            continue
        if not _CJK_ONLY.match(word):
            continue
        tokens = code.split()
        if len(tokens) < 2:
            continue
        words.setdefault(word, set()).add(" ".join(tokens))

    with open(output_path, "w", encoding="utf-8") as f:
        for word in sorted(words):
            readings = "|".join(sorted(words[word]))
            f.write(f"{word}\t{readings}\n")
    return len(words)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dict", type=Path, required=True, help="Assembled dict.yaml")
    parser.add_argument("--output", type=Path, required=True, help="Output wordlist path")
    args = parser.parse_args(argv)
    count = generate_wordlist(args.dict, args.output)
    print(f"Written: {args.output} ({count} words)")


if __name__ == "__main__":
    main()
