"""Static site pages (docs/): shared header navigation.

The landing page, POJ page and browser playground are hand-written HTML with
a copied header. Drift is invisible until a visitor on one page cannot reach
another, so the nav targets are pinned to be identical on every page.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).parents[1]
SITE = "https://taigi.anatomind.com/"
# page file -> its public URL (relative links resolve against it)
PAGES = {
    "docs/index.html": SITE,
    "docs/poj.html": SITE + "poj.html",
    "docs/try/index.html": SITE + "try/",
}


class _NavLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_nav = False
        self.links: list[list[str]] = []
        self._href: str | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "nav" and "site-nav" in (a.get("class") or "").split():
            self.in_nav = True
        elif tag == "a" and self.in_nav:
            self._href = a.get("href") or ""
            self.links.append([self._href, ""])

    def handle_endtag(self, tag):
        if tag == "nav":
            self.in_nav = False
        elif tag == "a":
            self._href = None

    def handle_data(self, data):
        if self._href is not None:
            self.links[-1][1] += data.strip()


def nav_targets(page: str) -> list[tuple[str, str]]:
    parser = _NavLinks()
    parser.feed((ROOT / page).read_text(encoding="utf-8"))
    out = []
    for href, text in parser.links:
        url = urljoin(PAGES[page], href).replace("/index.html", "/")
        out.append((url, text))
    return out


def test_header_nav_is_identical_on_every_page():
    """首頁、POJ 頁、網頁試拍頂懸的導覽愛仝款 (目標網址佮文字攏仝)。"""
    expected = nav_targets("docs/index.html")
    assert any(url == SITE + "try/" for url, _ in expected), "首頁導覽愛有網頁試拍"
    for page in PAGES:
        assert nav_targets(page) == expected, page


class _Head(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self.links: dict[str, str] = {}
        self.jsonld: list[str] = []
        self.h1 = 0
        self._in_ld = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                self.meta[key] = a.get("content") or ""
        elif tag == "link" and a.get("rel"):
            self.links[a["rel"]] = a.get("href") or ""
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._in_ld = True
            self.jsonld.append("")
        elif tag == "h1":
            self.h1 += 1

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_ld = False

    def handle_data(self, data):
        if self._in_ld:
            self.jsonld[-1] += data


def test_try_page_has_search_and_share_metadata_like_other_pages():
    """網頁試拍愛會予搜尋/分享揣著: canonical、og/twitter、JSON-LD、sitemap 一致。"""
    import json

    head = _Head()
    head.feed((ROOT / "docs/try/index.html").read_text(encoding="utf-8"))
    canonical = SITE + "try/"
    assert head.links["canonical"] == canonical
    assert head.meta["description"]
    assert head.meta["og:url"] == canonical
    for key in ("og:title", "og:description", "og:image", "twitter:card", "twitter:title"):
        assert head.meta.get(key), key
    assert head.h1 == 1
    graph = [node for block in head.jsonld for node in json.loads(block)["@graph"]]
    page = next(n for n in graph if n["@type"] == "WebPage")
    assert page["@id"] == canonical and page["url"] == canonical
    assert any(n["@type"] == "WebApplication" and n["url"] == canonical for n in graph)
    assert f"<loc>{canonical}</loc>" in (ROOT / "docs/sitemap.xml").read_text(encoding="utf-8")
