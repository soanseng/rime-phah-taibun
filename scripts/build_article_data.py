# ruff: noqa: RUF001, RUF002 - 台文原文佮規則用全形標點
"""讀文章蓋趣味 文章資料建置 => docs/read/data/articles.json + docs/read/audio/.

來源: 教育部《咱來學臺灣台語 讀文章蓋趣味》01、02 冊 (本土語文系列 0401-01、0402-01).
- 文字: OpenFormosa/OpenTaigi 已經用 PyMuPDF 照 PDF 實際顯示的圖層抽好的版面行
  (public/data/html-curriculum.json), 這爿干焦重組段落, 無重抽 PDF.
- 音檔: Taiwanese-Corpus/Lan-Lai-Oh-Taigi mp3/04/ (檔名照電子冊), 轉做單聲道 32 kbps MP3.
兩个來源攏釘 commit, 重建結果袂綴上游變.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OPENTAIGI_COMMIT = "46996838ad0560a8bbb3db44494a5a2dc9577284"
UPSTREAM_COMMIT = "3a8ffeb6e2e9d5c7eeb54173a41d6ad06b325d8b"
OPENTAIGI_RAW = f"https://raw.githubusercontent.com/OpenFormosa/OpenTaigi/{OPENTAIGI_COMMIT}/public/data"
UPSTREAM_MP3 = f"https://raw.githubusercontent.com/Taiwanese-Corpus/Lan-Lai-Oh-Taigi/{UPSTREAM_COMMIT}/mp3/04"
CACHE_DIR = REPO_ROOT / "data" / "article-cache"
OUT_JSON = REPO_ROOT / "docs" / "read" / "data" / "articles.json"
OUT_AUDIO = REPO_ROOT / "docs" / "read" / "audio"
USER_AGENT = "rime-phah-taibun-build/1.0 (https://taigi.anatomind.com)"

BOOKS = {
    1: {
        "id": "articles-1",
        "series": "0401-01",
        "pdf": "https://language.moe.gov.tw/upload/download/jts/04%E6%96%87%E7%AB%A01.pdf",
    },
    2: {
        "id": "articles-2",
        "series": "0402-01",
        "pdf": "https://language.moe.gov.tw/upload/download/jts/04%E6%96%87%E7%AB%A02.pdf",
    },
}

# 分類頁 (隔頁) 的字: 「𨑨迌」佇 PDF 是造字, 抽出來干焦賰「臺灣好」.
CATEGORIES = {
    "臺灣好": "臺灣好𨑨迌",
    "台灣好": "臺灣好𨑨迌",
    "臺灣好食物": "臺灣好食物",
    "台灣好食物": "臺灣好食物",
    "臺灣人情味": "臺灣人情味",
    "臺灣文史古": "臺灣文史古",
    "臺灣心適代": "臺灣心適代",
}

# 手冊字型的私用區字 → 教育部標準字 (照詞彙學習的讀音佮主字典對過).
PUA = {
    "\ue701": "𪜶",  # in
    "\ue705": "𬦰",  # peh
    "\ue703": "𫞼",  # tshāi
    "\uf5e9": "𫝏",  # gàn
    "\ue35c": "𫝛",  # siāng
}
PUA_RE = re.compile("[\ue000-\uf8ff\U000f0000-\U0010ffff]")

META = {
    "source": (
        "教育部《咱來學臺灣台語 讀文章蓋趣味》01、02 冊；短文出處為教育部電子報「臺灣閩南語我嘛會」、「閱讀越懂閩客語」"
    ),
    "url": "https://language.moe.gov.tw/",
    "pdf": [book["pdf"] for book in BOOKS.values()],
    "text": f"https://github.com/OpenFormosa/OpenTaigi/tree/{OPENTAIGI_COMMIT}",
    "audio": f"https://github.com/Taiwanese-Corpus/Lan-Lai-Oh-Taigi/tree/{UPSTREAM_COMMIT}/mp3/04",
    "note": "原文原音照引，著作權屬教育部；音檔轉做單聲道 32 kbps MP3",
}

SENT_END = ("。", "！", "？", "」", "』", "…", "：", "；")
_ROMAN = "A-Za-z\u00c0-\u024f\u0300-\u036f\u0358\u207f"
ROMAN_PAREN = rf"\(([{_ROMAN}][{_ROMAN}\- ']*)\)"
ANNOT_RE = re.compile(rf"\s*{ROMAN_PAREN}\s*")
HAN_RE = re.compile(r"[\u3400-\u9fff\U00020000-\U0003134f]")
QUOTES = "「」『』"
VOCAB_RE = re.compile(r"^(\d+)\.【(.+?)】(.*?)：(.*)$")
GRAMMAR_RE = re.compile(r"^(【.+?】(?:[^：(【]*【.+?】)?)(?:\((.+?)\))?：?(.*)$")
AUTHOR_RE = re.compile(r"作\s*者\s*：\s*(\S+)\s*$")
NOTE_RE = re.compile(r"^註\s*：\s*")
SIDE_HEADINGS = ("詞彙學習", "文法學習", "※本文出處")
SOURCE_RE = re.compile(
    r"教育部電子報\s*[—－─-]\s*(?P<paper>.+?)(?P<issue>\d+)期(?:（(?P<date>\d{4}-\d{2}-\d{2})）)?：\s*(?P<title>.+)$"
)
AUDIO_RE = re.compile(r"^04(\d)\d-(\d+)(?:-(\d+|[A-Z]))?＊?\.mp3$")


def local_name(name: str) -> str:
    """上游檔名有 ＊ 記號 (0402-21-01＊.mp3), 網站檔名提掉."""
    return name.replace("＊", "")


def fix_pua(text: str) -> str:
    """私用區字換標準字; 毋捌的私用區字直接報錯, 毋通偷偷留落來."""
    out = "".join(PUA.get(ch, ch) for ch in text)
    bad = PUA_RE.search(out)
    if bad:
        raise ValueError(f"未對應的私用區字 U+{ord(bad.group()):04X}: {out}")
    return out


def strip_annotations(text: str) -> str:
    """提掉內文的括號羅馬字 (官方讀音註), 賰漢羅本文; 毋是羅馬字的括號保留."""
    return ANNOT_RE.sub("", text).strip()


def toneless(syllable: str) -> str:
    """台羅音節去調號、細寫 (lâng → lang), 對音節表用."""
    text = unicodedata.normalize("NFD", syllable.lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def annotations(text: str, syllables: set[str] | None = None) -> list[dict]:
    """內文 '漢字(羅馬字)' 配對: 音節數 = 前面連續漢字數 (跳過引號), 漢字無夠就無算.

    syllables (主字典去調音節表) 有傳: 括號內有音節毋佇表內 (英文夾註, 像 Edinburgh) 就毋算讀音.
    at = 漢字佇 strip_annotations() 清本文的位置 (codepoint), 予後壁的羅馬字轉換換官方讀音.
    """
    out = []
    removed = 0
    for match in ANNOT_RE.finditer(text):
        tl = match.group(1).strip()
        parts = [s for s in re.split(r"[\s-]+", tl) if s]
        count = len(parts)
        head = text[: match.start()]
        quotes = len(head) - len(head.rstrip(QUOTES))
        head = head[: len(head) - quotes]
        han = head[-count:] if count <= len(head) else ""
        valid = syllables is None or all(toneless(s) in syllables for s in parts)
        if valid and len(han) == count and all(HAN_RE.match(ch) for ch in han):
            out.append({"han": han, "tl": tl, "at": match.start() - removed - quotes - count})
        removed += match.end() - match.start()
    return out


def load_syllables(path: Path = REPO_ROOT / "schema" / "phah_taibun.dict.yaml") -> set[str]:
    """主字典編碼欄的去調音節 (詞條第二欄, 空白分音節)."""
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        cols = line.split("\t")
        if len(cols) >= 2 and cols[1] and not line.startswith("#"):
            out.update(re.sub(r"\d", "", s) for s in cols[1].split())
    return out


def join_paragraphs(blocks: list[str]) -> list[str]:
    """無句尾標點的段是予人切斷的, 佮後一段接做伙."""
    out: list[str] = []
    carry = ""
    for block in blocks:
        carry += block.strip()
        if carry.endswith(SENT_END):
            out.append(carry)
            carry = ""
    if carry:
        out.append(carry)
    return out


def _join(prev: str, nxt: str) -> str:
    """接續行: 前後攏是羅馬字母才補空白 (華文、標點直接接)."""
    if re.search(rf"[{_ROMAN}]$", prev) and re.match(rf"[{_ROMAN}]", nxt):
        return f"{prev} {nxt}"
    return prev + nxt


def parse_side_notes(lines: list[dict]) -> dict:
    """右爿欄: 詞彙學習 (編號詞)、文法學習 (【詞】說明)、※本文出處."""
    vocab: list[dict] = []
    grammar: list[dict] = []
    source_text = ""
    section = None
    for line in lines:
        text = fix_pua(line["text"].strip())
        if not text:
            continue
        if text in ("詞彙學習", "文法學習"):
            section = text
            continue
        if text.startswith("※本文出處："):
            section = "source"
            source_text = text.removeprefix("※本文出處：")
            continue
        if section == "source":
            source_text = _join(source_text, text)
            continue
        vocab_match = VOCAB_RE.match(text) if section == "詞彙學習" else None
        grammar_match = GRAMMAR_RE.match(text) if section == "文法學習" else None
        if vocab_match:
            n, han, tl, hoa = vocab_match.groups()
            vocab.append({"n": int(n), "han": han, "tl": tl.strip(), "hoa": hoa.strip()})
        elif grammar_match:
            head, tl, body = grammar_match.groups()
            bare = None if tl else re.match(rf"^([{_ROMAN}][{_ROMAN}\- ']*)：(.*)$", body)
            if bare:
                tl, body = bare.groups()
            grammar.append({"han": re.sub("[【】]", "", head), "tl": (tl or "").strip(), "text": body.strip()})
        elif section == "詞彙學習" and vocab:
            vocab[-1]["hoa"] = _join(vocab[-1]["hoa"], text)
        elif section == "文法學習" and grammar:
            grammar[-1]["text"] = _join(grammar[-1]["text"], text)
    for item in vocab:
        item["hoa"] = taigi_name(item["hoa"])
    for item in grammar:
        item["text"] = taigi_name(item["text"])
    return {"vocab": vocab, "grammar": grammar, "source": parse_source(source_text) if source_text else None}


def taigi_name(text: str) -> str:
    """手冊說明文的語言名照國家語言名稱改叫「台語」(引用的刊名毋改, 毋經過這个函式)."""
    return text.replace("閩南語", "台語")


def parse_source(text: str) -> dict:
    match = SOURCE_RE.search(text)
    if match is None:
        raise ValueError(f"出處格式毋捌: {text}")
    return {
        "text": text,
        "paper": match["paper"].strip(),
        "issue": int(match["issue"]),
        "date": match["date"],
        "title": match["title"].strip(),
    }


def split_audio(names: list[str]) -> dict:
    """04{冊}-{頁}.mp3 = 全文; -{nn} = 第 nn 个詞; -{A,B} = 文法."""
    out: dict = {"article": None, "vocab": {}, "grammar": []}
    for name in names:
        match = AUDIO_RE.match(name)
        if match is None:
            raise ValueError(f"音檔名毋捌: {name}")
        tail = match.group(3)
        if tail is None:
            if out["article"] is not None:
                raise ValueError(f"一頁有兩个全文音檔: {out['article']}, {name}")
            out["article"] = name
        elif tail.isdigit():
            out["vocab"][int(tail)] = name
        else:
            out["grammar"].append(name)
    return out


def _fetch(url: str, dest: Path) -> Path:
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        dest.write_bytes(data)
    return dest


def load_source(name: str) -> dict:
    path = _fetch(f"{OPENTAIGI_RAW}/{name}", CACHE_DIR / OPENTAIGI_COMMIT / name)
    return json.loads(path.read_text(encoding="utf-8"))


def _divider(page: dict) -> str | None:
    """分類隔頁: 規頁干焦標題, 頭一行是分類名."""
    lines = page["lines"]
    if lines and all(line["role"] == "title" for line in lines):
        return CATEGORIES.get(lines[0]["text"].strip())
    return None


def build_book(number: int, layout: dict, hotspots: dict, syllables: set[str] | None = None) -> list[dict]:
    """一冊: 照頁序行, 遇著分類隔頁就換分類, 有全文音檔的頁就是一篇文章."""
    book = BOOKS[number]
    layout_book = next(b for b in layout["books"] if b["id"] == book["id"])
    hot_book = next(b for b in hotspots["books"] if b["id"] == book["id"])
    hot_pages = {p["number"]: [h["filename"] for h in p["hotspots"] if h.get("filename")] for p in hot_book["pages"]}
    articles = []
    category = None
    for page in layout_book["pages"]:
        divider = _divider(page)
        if divider:
            category = divider
            continue
        names = hot_pages.get(page["number"], [])
        audio = split_audio(names) if names else None
        if not audio or audio["article"] is None:
            continue
        if category is None:
            raise ValueError(f"第 {page['number']} 頁文章頭前無分類隔頁")
        articles.append(build_article(number, page, audio, category, syllables))
    return articles


def assemble_body(left: list[dict], right: list[dict]) -> dict:
    """左爿欄 + 右爿欄「詞彙學習」頭前的續文 → 標題、段落、作者、註."""
    title = None
    author = None
    blocks: list[str] = []
    notes: list[str] = []
    right_body = []
    for block in right:
        if block["text"].strip().startswith(SIDE_HEADINGS):
            break
        right_body.append(block)
    for block in [*left, *right_body]:
        text = fix_pua(block["text"].strip())
        if not text:
            continue
        if block["role"] == "title" and title is None and not blocks:
            title = text
            continue
        if NOTE_RE.match(text):
            notes.append(NOTE_RE.sub("", text))
            continue
        match = AUTHOR_RE.search(text)
        if match:
            author = match.group(1)
            text = text[: match.start()].strip()
        if text:
            blocks.append(text)
    return {"title": title, "author": author, "notes": notes, "paragraphs": join_paragraphs(blocks)}


def grammar_audio(entries: int, clips: list[str]) -> list[list[str]]:
    """文法音檔照順序分予逐條; 音檔比條數濟, 賰的攏歸上尾一條 (像【9月】與【9月初】有 A、B 兩音)."""
    out: list[list[str]] = [[] for _ in range(entries)]
    for i, clip in enumerate(clips):
        out[min(i, entries - 1)].append(clip)
    return out


def build_article(number: int, page: dict, audio: dict, category: str, syllables: set[str] | None = None) -> dict:
    columns = {c["side"]: c["blocks"] for c in page["columns"]}
    right_lines = [ln for ln in page["lines"] if ln["column"] == "right" and ln["role"] != "meta"]
    body = assemble_body(columns.get("left", []), columns.get("right", []))
    side = parse_side_notes(right_lines)
    if side["source"] is None:
        raise ValueError(f"第 {page['number']} 頁揣無出處")
    if len(audio["grammar"]) < len(side["grammar"]) or (audio["grammar"] and not side["grammar"]):
        raise ValueError(f"第 {page['number']} 頁文法 {len(side['grammar'])} 條、音檔 {audio['grammar']}")
    title = body["title"] or side["source"]["title"]
    clips = {}

    def rel(name: str | None) -> str | None:
        if name is None:
            return None
        clips[local_name(name)] = name
        return f"audio/{local_name(name)}"

    vocab = [{**item, "audio": rel(audio["vocab"].get(item["n"]))} for item in side["vocab"]]
    grammar = (
        [
            {**item, "audio": [rel(clip) for clip in clips_for]}
            for item, clips_for in zip(
                side["grammar"], grammar_audio(len(side["grammar"]), audio["grammar"]), strict=True
            )
        ]
        if side["grammar"]
        else []
    )
    return {
        "id": local_name(audio["article"]).removesuffix(".mp3"),
        "book": number,
        "page": int(AUDIO_RE.match(audio["article"]).group(2)),
        "category": category,
        "title": title,
        "author": body["author"],
        "notes": body["notes"],
        "source": side["source"],
        "audio": rel(audio["article"]),
        "paragraphs": [
            {"raw": p, "text": strip_annotations(p), "readings": annotations(p, syllables)} for p in body["paragraphs"]
        ],
        "vocab": vocab,
        "grammar": grammar,
        "_clips": clips,
    }


def transcode(src: Path, dst: Path) -> None:
    """照 build_listen_data.py: 單聲道 22.05 kHz 32 kbps, 提掉 metadata."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-map_metadata",
            "-1",
            "-ac",
            "1",
            "-ar",
            "22050",
            "-b:a",
            "32k",
            str(dst),
        ],
        check=True,
    )


def pull_audio(local: str, upstream: str, book: int) -> None:
    dst = OUT_AUDIO / local
    if dst.exists():
        return
    url = f"{UPSTREAM_MP3}/0{book}/{urllib.parse.quote(upstream)}"
    transcode(_fetch(url, CACHE_DIR / "mp3" / local), dst)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-audio", action="store_true", help="干焦重建 JSON, 毋下載轉檔音檔")
    args = parser.parse_args(argv)
    layout = load_source("html-curriculum.json")
    hotspots = load_source("curriculum.json")
    syllables = load_syllables()
    articles = [a for n in BOOKS for a in build_book(n, layout, hotspots, syllables)]
    wanted = set()
    for art in articles:
        for local, upstream in art.pop("_clips").items():
            wanted.add(local)
            if not args.skip_audio:
                pull_audio(local, upstream, art["book"])
    if not args.skip_audio:
        for stale in OUT_AUDIO.glob("*.mp3"):
            if stale.name not in wanted:
                stale.unlink()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {"meta": META, "articles": articles}
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    size = sum(p.stat().st_size for p in OUT_AUDIO.glob("*.mp3")) if OUT_AUDIO.exists() else 0
    print(f"{len(articles)} 篇, {len(wanted)} 音檔 ({size / 1e6:.1f} MB) → {OUT_JSON.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
