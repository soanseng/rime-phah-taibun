"""Landing-page stats must be computed from the shipped dictionary.

The #data visuals on docs/index.html quote dictionary statistics (entry
count, word-length distribution, multi-reading characters). This suite
recomputes every number from schema/phah_taibun.dict.yaml and pins the
rendered values, so the landing page can never show made-up or stale
figures; detailed research text lives in docs/research.md instead.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from scripts.tl_poj_convert import poj_diacritics_to_tone_numbers

ROOT = Path(__file__).parents[1]
INDEX = ROOT / "docs" / "index.html"
DICT = ROOT / "schema" / "phah_taibun.dict.yaml"
RESEARCH = ROOT / "docs" / "research.md"


def _dict_entries() -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line in DICT.read_text(encoding="utf-8").splitlines():
        if line.startswith(("#", "name:", "version:", "sort:", "...", "---")) or "\t" not in line:
            continue
        parts = line.split("\t")
        entries.append((parts[0], parts[1]))
    return entries


def _syllables(reading: str) -> int:
    return max(reading.count("-") + 1, len(reading.split()))


def test_landing_entry_count_matches_dictionary():
    total = len(_dict_entries())
    html = INDEX.read_text(encoding="utf-8")
    assert f"{total:,}" in html, f"landing must show the real entry count {total:,}"


def test_landing_wordlength_chart_matches_dictionary():
    entries = _dict_entries()
    total = len(entries)
    buckets: dict[str, int] = {"1": 0, "2": 0, "3": 0, "4+": 0}
    for _word, reading in entries:
        n = _syllables(reading)
        buckets["4+" if n >= 4 else str(n)] += 1

    html = INDEX.read_text(encoding="utf-8")
    chart = re.search(r'<figure[^>]*id="chart-wordlength".*?</figure>', html, re.S)
    assert chart, "word-length chart missing"
    rows = re.findall(r'data-syllables="([^"]+)"[^>]*data-count="(\d+)"', chart.group(0))
    assert rows, "chart rows with data-count missing"
    rendered = dict(rows)
    for key, count in buckets.items():
        assert rendered.get(key) == str(count), f"{key}-syllable bucket: page {rendered.get(key)} vs dict {count}"
    assert sum(int(v) for v in rendered.values()) == total


def test_landing_multi_reading_stat_and_examples_match_dictionary():
    readings: dict[str, set[str]] = defaultdict(set)
    for word, reading in _dict_entries():
        readings[word].add(reading)
    multi = sum(1 for word, rs in readings.items() if len(word) == 1 and len(rs) >= 2)

    html = INDEX.read_text(encoding="utf-8")
    assert f"{multi:,}" in html, f"multi-reading character count {multi:,} missing"

    # Each example chip shows a hanzi with its diacritic readings; convert
    # them back to tone numbers and require every reading in the dictionary.
    chips = re.findall(r'<li class="multi-example"[^>]*>(\S+) — ([^<]+)</li>', html)
    assert len(chips) >= 3, "expected at least three multi-reading examples"
    for hanzi, shown in chips:
        for syllable in shown.split("·"):
            numbered = poj_diacritics_to_tone_numbers(syllable.strip())
            assert numbered in readings.get(hanzi, set()), (
                f"{hanzi} {syllable} (→{numbered}) not a dictionary reading"
            )


def test_research_page_holds_moved_details():
    md = RESEARCH.read_text(encoding="utf-8")
    for marker in ("楊允言", "建置流程", "外部資源", "一字多音"):
        assert marker in md, marker
    sidebar = (ROOT / "docs" / "_sidebar.md").read_text(encoding="utf-8")
    assert "research.md" in sidebar
    sitemap = (ROOT / "docs" / "sitemap.xml").read_text(encoding="utf-8")
    assert "research.md" in sitemap


def test_landing_dense_research_blocks_moved_off():
    html = INDEX.read_text(encoding="utf-8")
    for gone in ("resource-ledger", "craft-grid", "pipeline-card", "research-note"):
        assert gone not in html, f"{gone} should live in docs/research.md, not the landing page"
