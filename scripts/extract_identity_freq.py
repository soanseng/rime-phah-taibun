"""Extract per-identity (hanzi, TL) word counts from iCorpus parallel files.

iCorpus ships line- and token-aligned Taiwanese files:
  自動標人工改漢字.txt (hanzi) ↔ 自動標人工改音標.txt (romanization)
Counting token pairs gives corpus evidence per (hanlo, kip_input) identity,
which distinguishes same-code homophones (人/膿 both lang5) that TL-only
frequency tables cannot separate.
"""

import argparse
import re
from collections import Counter
from pathlib import Path

# A corpus romanization token is countable when it is lowercase TL with at
# least one tone digit (particles without digits are skipped: they are rare
# and mostly punctuation-adjacent noise in this source).
_TL_TOKEN = re.compile(r"^[a-z][a-z0-9]*(?:--?[a-z0-9]+)*$")
_TONE_DIGIT = re.compile(r"[1-9]")
_CJK = re.compile(r"[\u3400-\u9fff]")


def _countable_tl(token: str) -> bool:
    return bool(_TL_TOKEN.fullmatch(token)) and bool(_TONE_DIGIT.search(token))


def extract_identity_counts(han_file, tl_file) -> Counter:
    """Count aligned token pairs from open text files.

    Args:
        han_file: iterable of lines, whitespace-tokenized Taiwanese hanzi
        tl_file: iterable of lines, whitespace-tokenized TL romanization

    Returns:
        Counter mapping (hanzi_token, tl_token) → occurrence count
    """
    counts: Counter = Counter()
    for han_line, tl_line in zip(han_file, tl_file, strict=False):
        han_tokens = han_line.split()
        tl_tokens = tl_line.split()
        if len(han_tokens) != len(tl_tokens):
            continue
        for han, tl in zip(han_tokens, tl_tokens, strict=True):
            if not _CJK.search(han):
                continue
            if not _countable_tl(tl):
                continue
            counts[(han, tl)] += 1
    return counts


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--han", type=Path, required=True, help="Aligned hanzi text file")
    parser.add_argument("--tl", type=Path, required=True, help="Aligned TL romanization file")
    parser.add_argument("--output", type=Path, required=True, help="Output TSV (han\\tkip\\tcount)")
    args = parser.parse_args(argv)

    with open(args.han, encoding="utf-8") as f_han, open(args.tl, encoding="utf-8") as f_tl:
        counts = extract_identity_counts(f_han, f_tl)

    with open(args.output, "w", encoding="utf-8") as f:
        for (han, tl), n in counts.most_common():
            f.write(f"{han}\t{tl}\t{n}\n")
    print(f"Written: {args.output} ({len(counts)} identities)")


if __name__ == "__main__":
    main()
