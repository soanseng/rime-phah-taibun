"""Diagnostic: list dictionary rows whose Hanzi count differs from the
syllable count of their code.

Not a gate. Mismatches are legitimate for contractions (今仔日 kiann9 jit8)
and some source spellings, so nothing is rejected or dropped; the report is
for manual review of suspected data errors such as a multi-character word
carrying a one-syllable code (梅子雞 kue1).

Usage:
    uv run python scripts/audit_syllable_mismatch.py [schema/phah_taibun.dict.yaml]

Prints `word<TAB>han_count<TAB>syllables<TAB>code<TAB>weight` rows to stdout
(single-syllable codes first) and a summary to stderr.
"""

import re
import sys
from pathlib import Path

HAN_WORD_RE = re.compile(r"[\u3400-\u9fff\uf900-\ufaff\U00020000-\U0003ffff]+")


def find_mismatches(dict_path: Path) -> list[tuple[str, int, int, str, str]]:
    rows = []
    in_body = False
    for line in dict_path.read_text(encoding="utf-8").splitlines():
        if not in_body:
            in_body = line == "..."
            continue
        parts = line.split("\t")
        if len(parts) < 2 or not HAN_WORD_RE.fullmatch(parts[0]):
            continue
        syllables = len(parts[1].split())
        if len(parts[0]) != syllables:
            rows.append((parts[0], len(parts[0]), syllables, parts[1], parts[2] if len(parts) > 2 else ""))
    rows.sort(key=lambda r: (r[2] != 1, r[0]))
    return rows


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    dict_path = Path(args[0] if args else "schema/phah_taibun.dict.yaml")
    rows = find_mismatches(dict_path)
    for row in rows:
        print("\t".join(str(field) for field in row))
    single = sum(1 for row in rows if row[2] == 1 and row[1] >= 2)
    print(f"{len(rows)} mismatched rows; {single} multi-character words with one-syllable codes", file=sys.stderr)


if __name__ == "__main__":
    main()
