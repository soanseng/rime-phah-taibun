"""讀文章頁 (docs/read/): 教育部《咱來學臺灣台語 讀文章蓋趣味》01、02 冊 59 篇.

全文 (漢羅/台羅/白話字/對照)、官方讀音 ruby、全文佮詞彙音檔、詞彙表佮文法說明;
閣愛會跳去網頁試拍做打字練習佮聽寫.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
READ = ROOT / "docs/read"
ARTICLES = json.loads((READ / "data/articles.json").read_text(encoding="utf-8"))
ROMAN = json.loads((READ / "data/roman.json").read_text(encoding="utf-8"))
ARTS = ARTICLES["articles"]


def test_59_articles_in_two_books():
    """59 篇分兩冊 (01 三十篇、02 廿九篇), 每篇欄位攏愛齊."""
    assert len(ARTS) == 59
    assert sum(a["book"] == 1 for a in ARTS) == 30
    assert sum(a["book"] == 2 for a in ARTS) == 29
    for a in ARTS:
        assert re.fullmatch(r"\d{4}-\d{2}", a["id"]), a["id"]
        assert a["title"] and a["author"] and a["category"], a["id"]
        assert a["paragraphs"], a["id"]
        assert a["vocab"], a["id"]
        assert a["audio"].startswith("audio/") and a["audio"].endswith(".mp3"), a["id"]
        assert a["source"]["paper"] and a["source"]["issue"], a["id"]


def test_every_audio_clip_exists_locally():
    """全文、詞彙、文法的音檔攏愛佇 docs/read/audio/ (32 kbps mp3)."""
    audio_dir = READ / "audio"
    refs: list[str] = []
    for a in ARTS:
        refs.append(a["audio"])
        refs += [v["audio"] for v in a["vocab"]]
        refs += [clip for g in a["grammar"] for clip in g["audio"]]
    assert refs, "音檔清單袂使空"
    missing = [r for r in refs if not (audio_dir / Path(r).name).is_file()]
    assert not missing, missing[:5]


def test_roman_json_covers_every_paragraph_with_note():
    """roman.json 逐篇逐段攏有台羅佮白話字, meta.note 愛講是機器轉換."""
    assert "轉換" in ROMAN["meta"]["note"] and "音檔" in ROMAN["meta"]["note"]
    assert set(ROMAN["articles"]) == {a["id"] for a in ARTS}
    for a in ARTS:
        paras = ROMAN["articles"][a["id"]]
        assert len(paras) == len(a["paragraphs"]), a["id"]
        for p in paras:
            assert p["tl"] and p["poj"], a["id"]
            assert isinstance(p["w"], list)


def test_official_readings_pin_their_codepoint_offsets():
    """官方讀音 at = codepoint 位置: han 愛佇本文 hit 个位置出現, ruby 袂走位."""
    for a in ARTS:
        for p in a["paragraphs"]:
            for r in p["readings"]:
                assert p["text"][r["at"] : r["at"] + len(r["han"])] == r["han"], (a["id"], r)


def test_page_shell_follows_the_site_pattern():
    """頁面殼佮工具頁仝款: module 載 read.js、read.css、無 JavaScript 嘛有提示."""
    html = (READ / "index.html").read_text(encoding="utf-8")
    assert '<script type="module" src="./read.js?v=' in html
    assert "./read.css?v=" in html
    assert "<noscript>" in html
    assert 'id="read-root"' in html
    assert 'id="read-status"' in html


def test_article_view_has_audio_speed_and_four_text_modes():
    """文章頁: 全文 audio controls、1x/0.75x 掣、漢羅/台羅/白話字/對照四模式."""
    js = (READ / "read.js").read_text(encoding="utf-8")
    assert "<audio" in js and "controls" in js
    assert "0.75" in js and "playbackRate" in js
    for label in ("漢羅", "台羅", "白話字", "對照"):
        assert label in js, label
    assert "rubySegments" in js, "漢羅模式愛用官方讀音標 ruby"


def test_page_links_practice_and_dictation_of_each_article():
    """逐篇愛會跳去試拍頁: 打字練習 ../try/?article=<id>#practice、聽寫 ../try/?listen=article:<id>#listen."""
    js = (READ / "read.js").read_text(encoding="utf-8")
    assert "`../try/?article=${id}#practice`" in js or "../try/?article=" in js
    assert "../try/?listen=article:" in js and "#listen" in js


def test_vocab_table_shows_hoa_column_and_dictation_target():
    """詞彙表: 漢字/台羅/華語/🔊 欄位, 台羅會使空 (無讀音的詞), 華語欄位袂使空."""
    for a in ARTS:
        for v in a["vocab"]:
            assert v["han"] and v["hoa"], (a["id"], v)
            assert v["audio"].startswith("audio/")


def test_credits_section_names_every_source():
    """來源佮授權: 兩本手冊 PDF、電子報出處、OpenTaigi 文字、Lan-Lai-Oh-Taigi 音檔、機器轉換說明."""
    html = (READ / "index.html").read_text(encoding="utf-8")
    for pdf in ARTICLES["meta"]["pdf"]:
        assert pdf in html, pdf
    assert ARTICLES["meta"]["text"] in html
    assert ARTICLES["meta"]["audio"] in html
    assert "著作權屬教育部" in html
    assert "教育部電子報" in html
    js = (READ / "read.js").read_text(encoding="utf-8")
    assert "meta.note" in js or "roman.meta.note" in js, "顯示羅馬字時愛露出機器轉換說明"


def test_read_data_is_not_gitignored():
    """根目錄 .gitignore 的 data/ 會吞著 docs/read/data/ (study 首擺就按呢無去)."""
    r = subprocess.run(
        ["git", "check-ignore", "docs/read/data/articles.json", "docs/read/audio/0401-06.mp3"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert r.stdout.strip() == "", f"予 .gitignore 擋著: {r.stdout}"
