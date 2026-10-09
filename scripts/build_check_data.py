"""寫作檢查資料: 連字符詞表 => docs/check/data/hyphen-words.json.

寫作檢查「連字符」建議干焦用教典詞目, 而且愛是教育部例句家己連字號寫的:
「毋是 m̄-sī」是詞目, 毋過例句攏寫 m̄ sī (分開) => 毋收, 才袂建議 m̄-sī.
規則: 多音節詞目 (佇轉換詞典有收), 全部例句內底連字號寫法出現次數 >= 分開寫法.
例句攏無出現的詞目照收 (教典詞目本身就是連字號寫法).

用法: uv run python scripts/build_check_data.py [--csv PATH] [--dict PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_GLOB = "data/KipSutianDataMirror/public/*/bunji/kautian.csv"
DICT = ROOT / "docs" / "thak" / "data-public" / "dict.json"
OUT = ROOT / "docs" / "check" / "data" / "hyphen-words.json"

MARKER_RE = re.compile(r"[（(][^（）()]*[)）]")  # noqa: RUF001 - 全形括號 (替)
EXAMPLE_TL_RE = re.compile(r"[（(]([^（）()]*)[)）]\s*$", re.MULTILINE)  # noqa: RUF001


def _norm(s: str) -> str:
    return unicodedata.normalize("NFC", s).lower()


def _example_tokens(rows: list[dict[str, str]]) -> list[list[str]]:
    """全部例句的羅馬字 (每句括號內底) => 逐句的詞 token (空白佮輕聲 -- 隔開, 標點剝掉)."""
    out = []
    for row in rows:
        for m in EXAMPLE_TL_RE.finditer(row.get("例句") or ""):
            text = re.sub(r"[.,!?;:\"“”'‘’()…]", " ", _norm(m.group(1)))  # noqa: RUF001
            out.append([t for t in re.split(r"\s+|--", text) if t])
    return out


def _counters(sents: list[list[str]]) -> tuple[Counter, Counter]:
    """連字號詞 token 次數; 單音節 token 連紲 2-4 个 (空白隔) 的次數."""
    joined: Counter = Counter()
    spaced: Counter = Counter()
    for toks in sents:
        joined.update(toks)
        for n in (2, 3, 4):
            for i in range(len(toks) - n + 1):
                grp = toks[i : i + n]
                if all("-" not in t for t in grp):
                    spaced[" ".join(grp)] += 1
    return joined, spaced


def hyphen_words(rows: list[dict[str, str]], known: set[str]) -> list[str]:
    joined, spaced = _counters(_example_tokens(rows))
    out: set[str] = set()
    for row in rows:
        han = MARKER_RE.sub("", (row.get("漢字") or "").strip()).strip()
        roman = _norm((row.get("羅馬字") or "").strip())
        if han not in known or len(han) < 2 or "-" not in roman or "/" in roman:
            continue
        if joined[roman] >= spaced[roman.replace("--", " ").replace("-", " ")]:
            out.add(han)
    return sorted(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", type=Path, default=None)
    ap.add_argument("--dict", type=Path, default=DICT)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    csv_path = args.csv or sorted(ROOT.glob(CSV_GLOB))[-1]
    with open(csv_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    known = set(json.loads(args.dict.read_text(encoding="utf-8")))
    words = hyphen_words(rows, known)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": {
            "source": "教育部臺灣台語常用詞辭典 詞目+例句 (CC BY-ND 3.0 TW)",
            "rule": "多音節詞目, 例句連字號寫法次數 >= 分開寫法",
        },
        "words": words,
    }
    args.out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {args.out} ({len(words)} words)")


if __name__ == "__main__":
    main()
