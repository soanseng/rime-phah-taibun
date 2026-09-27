#!/usr/bin/env python3
"""Build data/dict.json for tl-poj-convert from rime-phah-taibun sources.

Reading order per word: curated weight desc -> corpus freq desc -> insertion.

Layers:
  base    itaigi (CC0) + taihoa (CC BY-SA 4.0) + sitbut (CC BY-SA 4.0)
  curated public: placenames (CC BY 3.0 TW, w700/650) + STTI (w600, 標示來源)
          local : + LKK hanlo_rules (w800, 待確認) + 900句分詞 pairs (w900, 待確認)
  freq    public: icorpus (CC BY 4.0)
          local : + ungian/pojbh/nmtl/kipsutian/900leku/kok4hau7/identity (混合/待確認)

Usage: python3 tools/build.py [--mode public|local] [--rime-dir DIR] [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

RIME_DEFAULT = Path(__file__).resolve().parents[2] / "rime-phah-taibun"
CT = "ChhoeTaigiDatabase/ChhoeTaigiDatabase/"

FREQ_PUBLIC = ["icorpus_freq.tsv"]
FREQ_LOCAL = FREQ_PUBLIC + ["ungian_freq.tsv", "pojbh_freq.tsv", "nmtl_freq.tsv",
                            "kipsutian_sent_freq.tsv", "900leku_freq.tsv",
                            "kok4hau7_freq.tsv", "identity_freq.tsv"]


def is_han_str(s: str) -> bool:
    return bool(s) and any(
        (0x3400 <= ord(c) <= 0x9FFF) or (0x20000 <= ord(c) <= 0x3FFFF) for c in s)


def tl_key(r: str) -> str:
    return re.sub(r"\d+", "", r.replace(" ", "-"))


def ensure_tsv(rime: Path, name: str, script: str, parser_args: list[str]) -> Path:
    out = rime / "data" / name
    if not out.exists() or out.stat().st_size == 0:
        subprocess.run([sys.executable, str(rime / "scripts" / script), *parser_args],
                       check=True, capture_output=True)
    return out


def build(mode: str, rime: Path, out_dir: Path) -> None:
    sys.path.insert(0, str(rime))
    from scripts import convert_chhoetaigi as cc

    def norm_reading(r: str) -> str:
        r = cc.unicode_tones_to_numeric(r.replace(" ", "-"))
        r = r.replace("-", " ")
        r = re.sub(r"\s+", " ", r).strip()
        # 900句分詞 light-tone control prefix: "0khi3" → "khi3" (0 before a letter)
        return re.sub(r"\b0(?=[a-z])", "", r)

    data = rime / "data"
    words: dict[str, list[str]] = {}
    gloss: dict[str, str] = {}
    manifest: dict[str, dict] = {}

    def reg(src: str, note: str) -> None:
        manifest[src] = {"entries": 0, "license": note}

    def add(han: str, reading: str, hoabun: str, src: str) -> None:
        reading = " ".join(reading.split())
        lst = words.setdefault(han, [])
        if reading not in lst:
            lst.append(reading)
        if hoabun and han not in gloss:
            gloss[han] = hoabun
        manifest[src]["entries"] += 1

    # ---- base
    reg("itaigi", "CC0 (iTaigi 華台對照典)")
    reg("taihoa", "CC BY-SA 4.0 (台華線頂對照典)")
    reg("sitbut", "CC BY-SA 4.0 (台灣植物名彙)")
    with open(data / CT / "ChhoeTaigi_iTaigiHoataiTuichiautian.csv", encoding="utf-8-sig") as f:
        for e in cc.parse_itaigi_csv(f):
            add(e["hanlo"], e["rime_key"], e["hoabun"], "itaigi")
    with open(data / CT / "ChhoeTaigi_TaihoaSoanntengTuichiautian.csv", encoding="utf-8-sig") as f:
        for e in cc.parse_taihoa_csv(f):
            add(e["hanlo"], e["rime_key"], e["hoabun"], "taihoa")
    with open(data / CT / "ChhoeTaigi_TaioanSitbutMialui.csv", encoding="utf-8-sig") as f:
        for e in cc.parse_generic_csv(f, "sitbut"):
            add(e["hanlo"], e["rime_key"], e["hoabun"], "sitbut")

    # ---- curated
    cur: dict[str, dict[str, int]] = {}

    def cur_add(han: str, reading: str, weight: int, hoabun: str, src: str) -> None:
        reading = norm_reading(reading)
        if not reading or not is_han_str(han):
            return
        # Sanity gate: a curated reading must have one syllable per Han char.
        # Mixed-script words (OK繃, A菜) are exempt from the count check.
        if not re.search(r"[A-Za-z]", han):
            n_han = sum(1 for c in han if is_han_str(c))
            n_syl = len([s for s in reading.split(" ") if s])
            if n_syl != n_han:
                return
        d = cur.setdefault(han, {})
        d[reading] = max(d.get(reading, 0), weight)
        if hoabun and han not in gloss:
            gloss[han] = hoabun
        manifest[src]["entries"] += 1

    reg("placenames", "CC BY 3.0 TW (教育部本土語言標注臺灣地名)")
    plc = ensure_tsv(rime, "placename_entries.tsv", "parse_placenames.py",
                     ["--input", str(data / "moe_placenames" / "odt"),
                      "--output", str(data / "placename_entries.tsv")])
    for line in open(plc, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) == 4:
            cur_add(p[1], p[2], int(p[3]), p[0], "placenames")

    reg("stti", "開放運用、標示來源 (教育部 STTI 學科術語臺灣台語對譯)")
    stti = ensure_tsv(rime, "stti_entries.tsv", "parse_stti.py",
                      ["--input", str(data / "stti_ttg" / "ttg_20241219.ods"),
                       "--output", str(data / "stti_entries.tsv")])
    for line in open(stti, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) == 3 and is_han_str(p[1]):
            cur_add(p[1], p[2], 600, p[0], "stti")

    # 900句分詞：上游 Taiwanese-Corpus repo 聲明 MIT；原始教材為新北市104學年度
    # 工作坊，公開頁面須標示來源。權重 900/550（單字對）。
    reg("le9ku3", "MIT（Taiwanese-Corpus repo 聲明；原始教材：新北市900例句工作坊，標示來源）")
    for line in open(data / "Sin1pak8tshi7_2015_900-le7ku3" / "minnan900.分詞",
                     encoding="utf-8"):
        for tok in line.split():
            if "｜" in tok:
                h, l = tok.split("｜", 1)
                h = h.replace("-", "")
                n_han = sum(1 for c in h if is_han_str(c))
                if n_han >= 2:
                    cur_add(h, l, 900, "", "le9ku3")
                elif n_han == 1:
                    cur_add(h, l, 550, "", "le9ku3")

    # LKK 用字表：使用者 2026-09-27 確認可用（非商用、標示來源）。
    reg("lkk", "使用者確認可用：非商用、標示來源 (LKK 李江却基金會用字表)")
    import yaml
    rules = yaml.safe_load(open(rime / "schema" / "hanlo_rules.yaml", encoding="utf-8"))
    for w, e in (rules or {}).items():
        if isinstance(e, dict) and e.get("type") == "han" and e.get("kip"):
            cur_add(w, str(e["kip"]), 800, str(e.get("hoabun", "")), "lkk")

    # 單字條手補（之/枵/植/臨）：讀音由本典既有複詞內證一致推得
    # （如 哭枵=khau3 iau1、扶植=hu5 sit8、肺腑之言 hi3 hu2 tsi1 gian5），
    # 未引入外部聚合典。權重 550＝同 le9ku3 單字。
    reg("charsiu", "curated：讀音內證自本典 CC0/BY-SA 複詞（之/枵/植/臨）")
    for ch, readings in [("之", ["tsi1"]), ("枵", ["iau1"]),
                         ("植", ["sit8"]), ("臨", ["lim5"])]:
        for r in readings:
            cur_add(ch, r, 550, "", "charsiu")

    # ---- freq
    freq: dict[str, int] = {}
    for fn in FREQ_LOCAL if mode == "local" else FREQ_PUBLIC:
        path = data / fn
        if not path.exists():
            continue
        for line in open(path, encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) == 2 and p[1].isdigit():
                k = re.sub(r"\d+", "", p[0])
                freq[k] = freq.get(k, 0) + int(p[1])

    # ---- merge
    # Reading order: curated weight desc, then corpus freq desc, then insertion.
    # Readings whose syllable count disagrees with the Han char count (mixed-
    # script words exempt) are demoted to the tail — kept as clickable
    # candidates, never shown first.
    def sane(han: str, reading: str) -> bool:
        if re.search(r"[A-Za-z]", han):
            return True
        n_han = sum(1 for c in han if is_han_str(c))
        n_syl = len([s for s in reading.split(" ") if s])
        return n_syl == n_han

    table: dict[str, list[str]] = {}
    for w, rs in words.items():
        ranked = sorted(rs, key=lambda r: freq.get(tl_key(r), 0), reverse=True)
        if w in cur:
            cs = [r for r, _ in sorted(cur[w].items(), key=lambda kv: -kv[1])]
            ranked = cs + [r for r in ranked if r not in cs]
        ok = [r for r in ranked if sane(w, r)]
        bad = [r for r in ranked if not sane(w, r)]
        table[w] = ok + bad
    for w, d in cur.items():
        if w not in table:
            cs = [r for r, _ in sorted(d.items(), key=lambda kv: -kv[1])]
            table[w] = [r for r in cs if sane(w, r)] + [r for r in cs if not sane(w, r)]

    payload = {w: {"r": rs, **({"h": gloss[w]} if w in gloss else {})}
               for w, rs in table.items()}
    out_dir.mkdir(parents=True, exist_ok=True)
    js = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    (out_dir / "dict.json").write_text(js, encoding="utf-8")

    # ---- 學習提示 hints.json：輕聲詞（依頻率 top 1200）＋華語直譯小提醒
    light = []
    for line in open(data / "lighttone_entries.tsv", encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) < 3 or "--" not in p[0]:
            continue
        if not is_han_str(p[0].replace("--", "").replace("，", "")):
            continue
        f = int(p[2]) if p[2].strip().isdigit() else 0
        parts = re.split(r"\s{2,}", p[1].strip())
        if len(parts) < 2:
            continue
        reading = "--".join(norm_reading(x) for x in parts)
        light.append({"han": p[0].replace("--", ""), "marked": p[0],
                      "reading": reading, "f": f})
    light.sort(key=lambda x: -x["f"])
    light = light[:1200]
    calque = [
        {"han": "的", "suggest": "ê（的）"},
        {"han": "了", "suggest": "矣（ah）"},
        {"han": "很", "suggest": "誠／足（tsiânn/tsiok）"},
        {"han": "在", "suggest": "佇（tī）"},
        {"han": "跟", "suggest": "佮／kap"},
        {"han": "和", "suggest": "佮（kap）"},
        {"han": "不", "suggest": "毋（m̄）／無（bô）"},
        {"han": "沒", "suggest": "無（bô）"},
        {"han": "把", "suggest": "共（kā）"},
        {"han": "被", "suggest": "予（hōo）"},
        {"han": "讓", "suggest": "予／hōo"},
        {"han": "都", "suggest": "攏（lóng）"},
        {"han": "也", "suggest": "嘛（mā）"},
        {"han": "再", "suggest": "閣（koh）"},
        {"han": "從", "suggest": "對（tuì）／tùi"},
    ]
    hints = {"lighttone": [{k: v for k, v in x.items() if k != "f"} for x in light],
             "calque": calque}
    (out_dir / "hints.json").write_text(
        json.dumps(hints, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # ---- bigrams.json：identity＋900句＋詞典短語＋教典例句
    #      uni/bigram/trigram（羅→漢 Viterbi 用）；twblg 例句 → examples.json
    seqs = []          # 詞序語料（(b)(c) 用 None 標缺詞邊界）
    uni = {}
    for line in open(data / "identity_freq.tsv", encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) == 3 and p[0] in table and p[2].strip().isdigit():
            uni[p[0]] = uni.get(p[0], 0) + int(p[2])
    bigrams = {}
    for line in open(data / "identity_bigrams.tsv", encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) != 5 or not p[4].strip().isdigit():
            continue
        a, b, c = p[0], p[2], int(p[4])
        if a in uni and b in uni and c >= 2:
            bigrams[f"{a}\t{b}"] = c

    # (a) 900句分詞（日常域）：uni 累積＋詞序入 seqs
    fen = data / "Sin1pak8tshi7_2015_900-le7ku3" / "minnan900.分詞"
    if fen.exists():
        n_tok = 0
        for line in open(fen, encoding="utf-8"):
            words_a = []
            for tok in line.split():
                if "｜" not in tok:
                    continue
                h, l = tok.split("｜", 1)
                h = h.replace("-", "")
                if is_han_str(h) and h in table:
                    words_a.append(h)
                    uni[h] = uni.get(h, 0) + 1
                    n_tok += 1
            if len(words_a) >= 2:
                seqs.append(words_a)
        print(f"  seqs +900句 ({n_tok} tokens)")

    # (b) 詞典長詞條自生（iTaigi/taihoa 群眾短語；CC0/BY-SA）
    def seg_han(text, tbl):
        # 未匹配字以 None 邊界標記——不橋接跨缺口的偽 bigram
        out, i = [], 0
        while i < len(text):
            hit = None
            for L in range(min(8, len(text) - i), 1, -1):
                cand = text[i:i + L]
                if any(not is_han_str(c) for c in cand):
                    continue
                if cand in tbl:
                    hit = cand
                    break
            if hit:
                out.append(hit)
                i += len(hit)
            else:
                if out and out[-1] is not None:
                    out.append(None)
                i += 1
        return out

    n_mine = 0
    for w in table:
        if 4 <= len(w) <= 12 and is_han_str(w):
            words_b = seg_han(w, table)
            if len(words_b) >= 2:
                seqs.append(words_b)
                n_mine += 1
    print(f"  seqs +{n_mine} dict-mined phrases")

    # (c) twblg 教典例句（音節=漢字數逐詞對齊）＋examples.json
    #     使用者 2026-09-27 確認 twblg 可公開（標示 CC BY-ND 3.0 TW 來源）
    examples: dict[str, list] = {}
    twblg_han = set()   # 教典例句漢文指紋（句子出處驗證用）
    tw = json.load(open(data / "moedict-data-twblg" / "dict-twblg.json", encoding="utf-8"))
    if isinstance(tw, dict):
        tw = list(tw.values())
    n_sent = 0
    for e in tw:
        for hx in e.get("heteronyms", []):
            for d in hx.get("definitions", []):
                for ex in d.get("example", []) or []:
                    m = re.match(r"￹(.+?)￺\s*(.+?)￻", ex)
                    if not m:
                        continue
                    han = "".join(c for c in m.group(1) if is_han_str(c))
                    han_clean = re.sub(r"[^\u3400-\u9fff]", "", han)
                    twblg_han.add(han_clean)
                    tl_words = [t for t in m.group(2).split()
                                if re.fullmatch(r"[A-Za-z\u00C0-\u024F0-9][A-Za-z\u00C0-\u024F0-9\u0300-\u036f\u0358-]*", t)]
                    syls = [len(t.split("-")) for t in tl_words]
                    if sum(syls) != len(han) or not tl_words:
                        continue
                    seq, pos = [], 0
                    for t, n in zip(tl_words, syls):
                        hw = han[pos:pos + n]
                        pos += n
                        if hw in table:
                            seq.append(hw)
                            uni[hw] = uni.get(hw, 0) + 1
                        else:
                            seq.append(None)  # 邊界：不橋接跨缺口
                    seqs.append(seq)
                    n_sent += 1
                    tl_text = " ".join(tl_words)
                    for w in seq:
                        if w is not None and len(examples.get(w, [])) < 2:
                            examples.setdefault(w, []).append([han, tl_text])
    print(f"  seqs +{n_sent} twblg sentences")
    (out_dir / "examples.json").write_text(
        json.dumps(examples, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    print(f"  examples.json: {len(examples)} words")

    m7 = rime / "schema" / "moe700.yaml"
    if m7.exists():
        n7 = 0
        for line in open(m7, encoding="utf-8"):
            w = line.strip().removeprefix("- ").strip()
            if w and is_han_str(w) and w in table:
                uni[w] = uni.get(w, 0) + 2
                n7 += 1
        print(f"  uni +{n7} from moe700")

    # ---- 詞序一次性計數：bigram＋trigram（None 邊界不橋接）
    # trigram 語料稀疏（短句為主），≥1 全收——bytes 換準確率
    trigrams = {}
    for words_s in seqs:
        for a, b in zip(words_s, words_s[1:]):
            if a is None or b is None:
                continue
            k = f"{a}\t{b}"
            bigrams[k] = bigrams.get(k, 0) + 1
        for a, b, c3 in zip(words_s, words_s[1:], words_s[2:]):
            if a is None or b is None or c3 is None:
                continue
            k3 = f"{a}\t{b}\t{c3}"
            trigrams[k3] = trigrams.get(k3, 0) + 1
    (out_dir / "bigrams.json").write_text(
        json.dumps({"uni": uni, "bigrams": bigrams, "trigrams": trigrams},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    # ---- sentences.json：句級練習——只收「佮教典原文核對著有重叠」的句子
    # （使用者 2026-09-27 准教典例句重發布，標示 CC BY-ND 3.0 TW 來源；
    #   例句.csv 其餘 2,324 句出處未驗證，剔除）。
    reg("le7csv", "教育部教典例句（CC BY-ND 3.0 TW，使用者 2026-09-27 准重發布、標示來源）——只收佮教典原文核對著的句子")
    import csv as _csv
    sents = []
    n_drop = 0
    liku = data / "Sin1pak8tshi7_2015_900-le7ku3" / "例句.csv"
    if liku.exists():
        with open(liku, encoding="utf-8") as f:
            for row in _csv.DictReader(f):
                han = (row.get("例句") or "").strip()
                tl = (row.get("例句標音") or "").strip()
                hoa = (row.get("華語翻譯") or "").strip()
                key = re.sub(r"[^\u3400-\u9fff]", "", han)
                if han and tl and key in twblg_han:
                    sents.append([han, tl, hoa])
                elif han and tl:
                    n_drop += 1
    (out_dir / "sentences.json").write_text(
        json.dumps({"s": sents}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    print(f"  sentences.json: {len(sents)} sentences")

    import gzip
    manifest["_meta"] = {"mode": mode, "words": len(table), "with_gloss": len(gloss)}
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[{mode}] words={len(table)} gloss={len(gloss)} "
          f"json={len(js)/1e6:.2f}MB gzip={len(gzip.compress(js.encode()))/1e6:.2f}MB")
    for k, v in manifest.items():
        if k != "_meta":
            print(f"  {k:10s} {v['entries']:7d}  {v['license']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["public", "local"], default="public")
    ap.add_argument("--rime-dir", type=Path, default=RIME_DEFAULT)
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).resolve().parent.parent / "data")
    a = ap.parse_args()
    build(a.mode, a.rime_dir, a.out)


if __name__ == "__main__":
    main()
