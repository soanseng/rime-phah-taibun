"""Landing-page Taiwanese copy must be typeable with the input method itself.

docs/index.html shows Han-roman text that doubles as SEO keywords (Pe̍h-ōe-jī,
Tâi-gí, …). This suite pins every visible word to the main dictionary and the
TL→POJ converter, so the copy can never drift from what the IME produces;
tests/test_real_rime.py additionally types the same words through the real
librime engine.
"""

from __future__ import annotations

import re
from pathlib import Path

from scripts.tl_poj_convert import tl_to_poj

ROOT = Path(__file__).parents[1]
INDEX = ROOT / "docs" / "index.html"
DICT = ROOT / "schema" / "phah_taibun.dict.yaml"

HERO_TAGLINE = "會曉講 Tâi-gí，就會曉 phah Tâi-bûn。"  # noqa: RUF001
INTENT_POJ = "我欲用 Pe̍h-ōe-jī 拍字"

# (visible hanzi term, dictionary TL reading with tone numbers) — every hanzi
# word shown in Han-roman copy on the page must exist in the main dictionary.
HANLO_TERMS = [
    ("台語", "tai5 gi2"),
    ("台文", "tai5 bun5"),
    ("白話字", "peh8 ue7 ji7"),
    ("會曉", "e7 hiau2"),
    ("講", "kong2"),
    ("拍", "phah4"),
    ("拍字", "phah4 ji7"),
    ("我欲", "gua2 beh4"),
]


def _index_html() -> str:
    return INDEX.read_text(encoding="utf-8")


def _dict_readings() -> dict[str, set[str]]:
    readings: dict[str, set[str]] = {}
    for line in DICT.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or "\t" not in line:
            continue
        word, reading = line.split("\t", 2)[:2]
        readings.setdefault(word, set()).add(reading)
    return readings


def test_hero_tagline_and_poj_intent_visible():
    html = _index_html()
    assert HERO_TAGLINE in html
    assert INTENT_POJ in html


def test_meta_keywords_cover_romanized_search_terms():
    html = _index_html()
    match = re.search(r'<meta name="keywords" content="([^"]*)"', html)
    assert match, "keywords meta tag missing"
    keywords = match.group(1)
    for term in (
        "Pe̍h-ōe-jī",
        "Tâi-gí",
        "Tâi-bûn",
        "Tâi-lô",
        "Hàn-lô",
        "Lô-má-jī",
        "台語鍵盤",
        "教羅",
        "教會羅馬字",
    ):
        assert term in keywords, term


def test_og_description_mentions_poj_romanization():
    html = _index_html()
    match = re.search(r'property="og:description" content="([^"]*)"', html)
    assert match, "og:description missing"
    assert "Pe̍h-ōe-jī" in match.group(1)


def test_jsonld_carries_romanized_keywords():
    html = _index_html()
    match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    assert match, "JSON-LD block missing"
    assert "Pe̍h-ōe-jī" in match.group(1)
    assert "Tâi-gí" in match.group(1)


def test_poj_letter_mapping_matches_converter():
    """The page's POJ form Pe̍h-ōe-jī maps to the dictionary reading of 白話字
    (peh8-ue7-ji7) via the converter's letter substitutions; the diacritic
    rendering itself is pinned by the real-engine test in test_real_rime.py."""
    assert tl_to_poj("peh8-ue7-ji7") == "peh8-oe7-ji7"


def test_visible_hanzi_terms_backed_by_main_dictionary():
    readings = _dict_readings()
    for word, reading in HANLO_TERMS:
        assert reading in readings.get(word, set()), f"{word} {reading} not in main dictionary"
