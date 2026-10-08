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
import unicodedata
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


def _reading_key(s: str) -> set[tuple[str, str]]:
    """羅馬字讀音 → (字母, 調符) 集合; 「leh/teh」「(接名詞)」等註記先剝, 大細字、-、--、空白無影響."""
    out = set()
    for alt in re.sub(r"\(.*?\)", "", s).split("/"):
        nfd = unicodedata.normalize("NFD", alt.lower().replace("\u0131", "i"))  # 700 表有無點 i (U+0131)
        letters = "".join(c for c in nfd if c.isascii() and c.isalpha())
        marks = "".join(sorted(c for c in nfd if unicodedata.category(c) == "Mn"))
        if letters:
            out.add((letters, marks))
    return out


def _kind(form: str) -> str:
    han = bool(HAN.search(form))
    roman = bool(re.search(r"[A-Za-z]", form))
    return "mix" if han and roman else "han" if han else "lo"


def build_yongji(moe_rows: list[dict], lkk_rows: list[dict]) -> list[dict]:
    """教育部 700 逐詞 + LKK 寫法分類 (漢字 han / 羅馬字 lo / 漢羅混 mix)."""
    by_moe: dict[str, list[str]] = {}
    lkk_han: set[str] = set()  # LKK 照寫漢字的詞
    for r in lkk_rows:
        form = r["建議用字"].strip()
        moe = r["教育部推薦漢字"].strip()
        reading = r["音讀"].strip()
        if not moe and HAN.search(reading) and not HAN.search(form):
            moe = reading  # 欄位錯位的列 (建議用字 ke-pô、音讀欄是 家婆)
        # 「教育部推薦漢字」欄有漢字、而且佮 LKK 寫法無仝, 才是「LKK 改寫」; 其他 (仝字、欄位錯位) 當做照寫漢字
        if moe and HAN.search(moe) and moe != form:
            by_moe.setdefault(moe, [])
            if form not in by_moe[moe]:
                by_moe[moe].append(form)
        elif form and HAN.search(form):
            lkk_han.add(form)
    items = []
    for r in moe_rows:
        word = r["建議用字"].strip()
        if not word:
            continue
        tl = _reading_key(r["音讀"])
        cands = by_moe.get(word, [])
        # 仝字多音: 干焦提讀音仝款的 LKK 羅馬字寫法; 漢羅混的無法度比讀音, 照收
        forms = [f for f in cands if _kind(f) == "lo" and _reading_key(f) & tl]
        if not forms:
            forms = [f for f in cands if _kind(f) == "mix"]
        # 調號無仝 (LKK liam-mi 無調符、700 liâm-mi): 去調字母對會著、而且干焦一个寫法才收
        if not forms:
            toneless = {letters for letters, _ in tl}
            loose = [f for f in cands if _kind(f) == "lo" and {x for x, _ in _reading_key(f)} & toneless]
            forms = loose if len(loose) == 1 else []
        # LKK 寫漢字的詞免比讀音: 腔口無仝 (家己 ka-kī / ka-tī) 寫法仝款
        if not forms and word in lkk_han:
            forms = [word]
        items.append(
            {
                "word": word,
                "tl": r["音讀"].strip(),
                "hoa": r["對應華語"].strip(),
                "alts": _split(r["異用字"]),
                "examples": [e.strip() for e in re.split(r"、", r["用例"] or "") if e.strip()],
                "lkk": [{"form": f, "kind": _kind(f)} for f in forms],
            }
        )
    return items


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", type=Path, default=ROOT / "data" / "700iongji.csv")
    ap.add_argument("--lkk", type=Path, default=ROOT / "data" / "lkk_yongji.csv")
    ap.add_argument(
        "--leku",
        type=Path,
        default=ROOT / "data" / "Sin1pak8tshi7_2015_900-le7ku3" / "minnan900.json",
    )
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "study" / "data" / "iongji.json")
    ap.add_argument("--out-yongji", type=Path, default=ROOT / "docs" / "study" / "data" / "yongji.json")
    args = ap.parse_args()
    with args.csv.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    with args.lkk.open(encoding="utf-8") as f:
        lkk_rows = list(csv.DictReader(f))
    leku = json.loads(args.leku.read_text(encoding="utf-8"))
    source = "教育部臺灣台語推薦用字700字詞 (建議用字、異用字、用例; yiufung/minnan-700 整理)"
    outputs = [
        (
            args.out,
            build_iongji(rows, leku),
            {
                "source": source,
                "sentences": "新北市104學年度閩南語字音字形900例句工作坊 (Taiwanese-Corpus, MIT; 標示來源)",
            },
        ),
        (
            args.out_yongji,
            build_yongji(rows, lkk_rows),
            {"source": source, "lkk": "李江却台語文教基金會 LKK 漢羅用字表 (標示來源)"},
        ),
    ]
    for path, items, meta in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        out = {"meta": meta, "items": items}
        path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"wrote {path} ({len(items)} items)")


if __name__ == "__main__":
    main()
