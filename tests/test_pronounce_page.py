"""拼音發音教學頁 (docs/pronounce/): 課程照教育部《學拼音有撇步》, 音檔連官方網址.

資料由 scripts/build_pronounce_data.py 對 refs/moe-jts-01-pinyin.pdf 產生 (PDF 版權所有, 無進 repo).
"""

from __future__ import annotations

import json
import re
import urllib.parse
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
DATA = ROOT / "docs/pronounce/data/lessons.json"
PAGE = ROOT / "docs/pronounce/index.html"
PDF = ROOT / "refs/moe-jts-01-pinyin.pdf"
OFFICIAL = "https://language.moe.gov.tw/upload/download/jts/01%E6%8B%BC%E9%9F%B3(%E9%9F%B3%E6%AA%94)/"


def _data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def _audio_refs(x) -> list[str]:
    out: list[str] = []
    if isinstance(x, dict):
        for k, v in x.items():
            if k in ("audio", "examplesAudio") and isinstance(v, str):
                out.append(v)
            else:
                out.extend(_audio_refs(v))
    elif isinstance(x, list):
        for v in x:
            out.extend(_audio_refs(v))
    return out


def test_course_follows_the_handbook_parts_and_ends_with_poj():
    """課程愛包含 韻母、聲母、聲調、變調, 上尾一課是進階白話字對照."""
    lessons = _data()["lessons"]
    parts = [ls["part"] for ls in lessons]
    for part in ("韻母", "聲母", "聲調", "變調"):
        assert part in parts, part
    assert lessons[-1]["id"] == "poj" and lessons[-1]["part"] == "進階"


def test_every_lesson_has_an_audio_backed_listening_quiz():
    """逐課攏有練習, 逐題攏有音檔佮答案, 答案袂使空."""
    for ls in _data()["lessons"]:
        pool = ls["quiz"]["pool"]
        assert len(pool) >= 3, ls["id"]
        for q in pool:
            assert q["audio"].endswith(".mp3") and q["answer"].strip(), (ls["id"], q)
        answers = {q["answer"] for q in pool}
        assert len(answers) >= 3 or ls["quiz"].get("options"), ls["id"]


def test_audio_plays_from_the_official_moe_url():
    """音檔版權所有, 毋放 repo: 連教育部官方 https 網址, 本機嘛無 audio/ 目錄."""
    assert _data()["audioBase"] == OFFICIAL
    assert not (ROOT / "docs/pronounce/audio").exists()
    for name in _audio_refs(_data()):
        assert re.fullmatch(r"0101-[0-9A-Za-z-]+\.mp3", name), name


def test_every_audio_is_one_the_handbook_links_to():
    """逐个音檔名攏愛是手冊藍字連結有的 (對錯音檔 = 教毋著音)."""
    pypdf = pytest.importorskip("pypdf")
    if not PDF.exists():
        pytest.skip("refs/ 無 PDF (版權所有, 無進 repo); 跑 build_pronounce_data.py 會下載")
    linked = set()
    for page in pypdf.PdfReader(str(PDF)).pages:
        for annot in page.get("/Annots") or []:
            uri = (annot.get_object().get("/A") or {}).get("/URI", "")
            if uri.endswith(".mp3"):
                linked.add(urllib.parse.unquote(uri).rsplit("/", 1)[1])
    used = set(_audio_refs(_data()))
    assert used - linked == set()
    assert len(used) >= 1100, "音節表、例字、練習的音檔愛攏用著"


def test_syllable_table_keeps_the_drawn_tone8_marks():
    """手冊第 8 調符是畫的線 (文字層無): 畫面看會著的 ta̍p bi̍t … 愛有, pat tat … 袂使加."""
    cells = {c["audio"]: c["tl"] for ls in _data()["lessons"] for t in ls.get("tables", []) for c in t["cells"]}
    seen = {
        "0101-32-tap.mp3": "ta̍p",
        "0101-32-bit.mp3": "bi̍t",
        "0101-32-tit.mp3": "ti̍t",
        "0101-32-thak.mp3": "tha̍k",
        "0101-32-lat.mp3": "la̍t",
        "0101-32-lah.mp3": "la̍h",
        "0101-32-lip.mp3": "li̍p",
        "0101-32-lik.mp3": "li̍k",
        "0101-32-pat.mp3": "pat",
        "0101-32-tat.mp3": "tat",
        "0101-32-pak.mp3": "pak",
        "0101-32-pah.mp3": "pah",
        "0101-32-thap.mp3": "thap",
        "0101-33-hmh.mp3": "hm̍h",
        "0101-35-ngiauh.mp3": "ngia̍uh",
        "0101-36-khennh.mp3": "khe̍nnh",
        "0101-32-jih.mp3": None,  # 書面調符看袂清, 先跳過
    }
    assert {k: cells.get(k) for k in seen} == seen


# 照手冊第 18-20 頁渲染畫面逐格對的第 8 調音節 (書面看袂清的 jih 跳過)
BOOK_TONE8 = set(
    [
        "bit",
        "bik",
        "tap",
        "tit",
        "thak",
        "lat",
        "lah",
        "lip",
        "lik",
        "kik",
        "khah",
        "hap",
        "hat",
        "hak",
        "hah",
        "gak",
        "gik",
        "tsip",
        "tsik",
        "tshak",
        "sah",
        "sip",
        "sit",
        "jip",
        "jit",
        "put",
        "poh",
        "but",
        "boh",
        "tut",
        "theh",
        "loh",
        "kut",
        "khok",
        "hoh",
        "hmh",
        "gok",
        "phauh",
        "phueh",
        "bueh",
        "piat",
        "biat",
        "tiap",
        "thiap",
        "lauh",
        "lueh",
        "liat",
        "hiap",
        "gueh",
        "giat",
        "tshauh",
        "jiap",
        "jiat",
        "khiak",
        "tshiak",
        "tioh",
        "liok",
        "lioh",
        "giah",
        "gioh",
        "siok",
        "ngiauh",
        "puat",
        "buat",
        "luat",
        "guat",
        "juah",
        "uah",
        "luaih",
        "khaunnh",
        "haunnh",
        "khennh",
    ]
)


def test_syllable_table_tone8_set_is_exactly_what_the_book_shows():
    """音節表有第 8 調符的格, 愛拄好是書面看會著的 72 格: 加一格就是教毋著調, 少一格就是漏抄."""
    cells = [c for ls in _data()["lessons"] for t in ls.get("tables", []) for c in t["cells"]]
    marked = {c["audio"].rsplit("-", 1)[1].removesuffix(".mp3") for c in cells if "\u030d" in c["tl"]}
    assert len(BOOK_TONE8) == 72
    assert marked == BOOK_TONE8
    assert not any(c["audio"].endswith("-jih.mp3") for c in cells)


def test_sandhi_lesson_has_the_supplementary_song_video_labelled_honestly():
    """第 11 課連續變調附〈八音之歌〉影片: 照實標題, 標「補充」, 毋通講是手冊的〈8調ê滋味〉."""
    sandhi = next(ls for ls in _data()["lessons"] if ls["id"] == "sandhi")
    video = sandhi["video"]
    assert video["youtube"] == "2Vgf2NyMOpc"
    assert "八音之歌" in video["title"] and "補充" in video["label"]
    assert "8調ê滋味" not in video["title"]


def test_page_credits_the_handbook_and_links_tailo():
    """頁面愛標示來源 (手冊 PDF、官方音檔) 佮連教育部台羅拼音學習網."""
    html = PAGE.read_text(encoding="utf-8")
    assert "https://language.moe.gov.tw/upload/download/jts/01%E6%8B%BC%E9%9F%B3.pdf" in html
    assert "學拼音有撇步" in html and "教育部" in html
    assert "https://tailo.moe.edu.tw/" in html
