"""Parse 教育部《讀文章蓋趣味》官方讀音 into a dictionary source TSV.

Source: docs/read/data/roman.json (committed; 文字著作權屬教育部, 佮讀文章
頁面仝款標示出處 — 見 AGENTS.md 關鍵外部資料來源表)。Only o:1 (詞, 讀音)
pairs are consumed: the book's 手冊括號官方讀音, never machine-converted
guesses (詞身份 invariant: 毋捏造來源無記載的組合).

Codes preserve 連讀輕聲 `--` as the double-space separator
(build_lighttone_entries.kip_to_rime_key 慣例 "tng2  lai5"), unlike the
supplement track which collapses it. Non-TL readings (親像冊內括號英文
"murphy's law1" 予 officialNumeric 提著) and 免調 tokens (validate_dict
fatal gate) are skipped and counted.

Output lines: 讀文章蓋趣味<TAB>詞<TAB>rime key — 佮 parse_stti 仝款予
build_all Step 3d 的 append gate (text, code) 去重了後照 tier 600 接入。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SOURCE_LABEL = "讀文章蓋趣味"

# 官方讀音音節: 數字調 1-9, 輕聲前置 --。
_TOKEN_RE = re.compile(r"(--)?([a-z]+[1-9])")


def official_to_rime_code(reading: str, syllabary: set[str] | None = None) -> str | None:
    """官方數字調讀音 → rime key; 輕聲 -- → 兩格空白, 無法度解析 → None。

    syllabary = 主字典出現過的音節 (免調 stem); 冊內英文夾註 (Edinburgh4)
    字母+調號會過形狀檢查, 愛靠 syllabary 擋。None = 退做形狀檢查。
    """
    parts: list[str] = []
    for token in reading.split(" "):
        match = _TOKEN_RE.fullmatch(token)
        if not match:
            return None
        light, syllable = match.groups()
        if syllabary is not None and re.sub(r"[0-9]+$", "", syllable) not in syllabary:
            return None
        parts.append(("  " if light else (" " if parts else "")) + syllable)
    return "".join(parts) if parts else None


def load_syllabary(dict_yaml: Path) -> set[str]:
    """對主字典代碼欄提音節表 (去調 stem); 檔案缺席回空集合。"""
    stems: set[str] = set()
    in_header = True
    for line in dict_yaml.read_text(encoding="utf-8").splitlines():
        if in_header:
            if line.startswith("..."):
                in_header = False
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        for token in parts[1].split():
            stems.add(re.sub(r"[0-9]+$", "", token.removeprefix("--")))
    return stems


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Parse MOE 讀文章蓋趣味 official readings")
    parser.add_argument("--input", type=Path, required=True, help="docs/read/data/roman.json")
    parser.add_argument("--output", type=Path, required=True, help="entries TSV (source\\than\\tcode)")
    parser.add_argument(
        "--syllabary",
        type=Path,
        default=None,
        help="主字典 dict.yaml; 供音節表擋英文夾註 (缺席退做形狀檢查)",
    )
    args = parser.parse_args(argv)

    syllabary = load_syllabary(args.syllabary) if args.syllabary and args.syllabary.exists() else None
    roman = json.loads(args.input.read_text(encoding="utf-8"))
    pairs: set[tuple[str, str]] = set()  # (詞, 讀音) o:1 組合, 逐組都收
    skipped = 0
    for paragraphs in roman["articles"].values():
        for para in paragraphs:
            for w in para["w"]:
                if not w.get("o") or not w.get("r"):
                    continue
                code = official_to_rime_code(w["r"], syllabary)
                if code is None:
                    skipped += 1
                    continue
                pairs.add((w["h"], code))

    with open(args.output, "w", encoding="utf-8") as out:
        for han, code in sorted(pairs):
            out.write(f"{SOURCE_LABEL}\t{han}\t{code}\n")
    print(
        f"  {len(pairs)} entries → {args.output}"
        f" ({skipped} skipped: 非 TL 官方讀音; syllabary={'Y' if syllabary else 'N'})"
    )


if __name__ == "__main__":
    sys.exit(main())
