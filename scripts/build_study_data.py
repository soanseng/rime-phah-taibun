"""檢定練習資料: 教育部推薦用字 700 的「異用字」→ docs/study/data/iongji.json.

用途:
- /study/iongji/ 用字選擇題 (推薦用字 vs 異用字, 例句挖空)
- /check/ 寫作檢查 (異用字 → 建議改推薦用字)

例句只用 700 表家己的「用例」佮新北市 900 例句 (MIT); 教典例句 CC BY-ND,
挖空會變做改作, 毋收.

用法: uv run python scripts/build_study_data.py
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPTIONAL = re.compile(r"[()（）/]")  # noqa: RUF001 - 700 表用全形括號標選擇性成分
MAX_SENTENCES = 3
HAN = re.compile(r"[\u3400-\u9fff\U00020000-\U0003ffff]")
SYL = re.compile(r"(?:[^\W\d_]|[\u0300-\u036f\u0358\u207f])+")


def _aligned(han: str, tl: str) -> bool:
    """漢字數+漢羅內羅馬字音節數 == 臺羅音節數, 而且臺羅無斷頭 (" -tsu"、"siōng- an")."""
    if re.search(r"(^|\s)-[^-]|[^-]-(\s|$)", tl):
        return False
    roman_in_han = SYL.findall(HAN.sub(" ", han))
    return len(HAN.findall(han)) + len(roman_in_han) == len(SYL.findall(tl))


def _split(field: str) -> list[str]:
    return [p.strip().strip('"「」') for p in re.split(r"[、/]", field or "") if p.strip()]


def build_iongji(rows: list[dict], leku: dict) -> list[dict]:
    recommended = {r["建議用字"].strip() for r in rows}
    sentences = [(e["例句漢字"], e["例句臺羅"]) for e in leku.values()]
    sentences = [(h, t) for h, t in sentences if _aligned(h, t)]
    items = []
    for r in rows:
        word = r["建議用字"].strip()
        if not word or OPTIONAL.search(word):
            continue
        alts = []
        for a in _split(r["異用字"]):
            if not OPTIONAL.search(a) and a != word and a not in alts:
                alts.append(a)
        if not alts:
            continue
        examples = [e.split("──")[0].strip() for e in re.split(r"、", r["用例"] or "")]
        examples = [e for e in examples if word in e]
        sents = [[h, t] for h, t in sentences if word in h][:MAX_SENTENCES]
        if not examples and not sents:
            continue
        items.append(
            {
                "word": word,
                "tl": r["音讀"].split("/")[0].strip(),
                "hoa": r["對應華語"].strip(),
                "alts": alts,
                "recAlts": [a for a in alts if a in recommended],
                "examples": examples,
                "sentences": sents,
            }
        )
    return items


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", type=Path, default=ROOT / "data" / "700iongji.csv")
    ap.add_argument(
        "--leku",
        type=Path,
        default=ROOT / "data" / "Sin1pak8tshi7_2015_900-le7ku3" / "minnan900.json",
    )
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "study" / "data" / "iongji.json")
    args = ap.parse_args()
    with args.csv.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    leku = json.loads(args.leku.read_text(encoding="utf-8"))
    items = build_iongji(rows, leku)
    out = {
        "meta": {
            "source": "教育部臺灣台語推薦用字700字詞 (建議用字、異用字、用例; yiufung/minnan-700 整理)",
            "sentences": "新北市104學年度閩南語字音字形900例句工作坊 (Taiwanese-Corpus, MIT; 標示來源)",
        },
        "items": items,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {args.out} ({len(items)} items)")


if __name__ == "__main__":
    main()
