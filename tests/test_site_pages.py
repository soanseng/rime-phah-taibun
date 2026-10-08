"""Static site pages (docs/): shared header navigation and per-page SEO.

The landing page, POJ page, browser playground and the web tools (轉換、詞彙、
文法) are hand-written HTML with a copied header. Drift is invisible until a
visitor on one page cannot reach another, so the nav targets are pinned to be
identical on every page.
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
    "docs/convert/index.html": SITE + "convert/",
    "docs/vocab/index.html": SITE + "vocab/",
    "docs/grammar/index.html": SITE + "grammar/",
    "docs/check/index.html": SITE + "check/",
    "docs/study/index.html": SITE + "study/",
}
TOOL_PAGES = ["convert", "vocab", "grammar", "check"]
STUDY_PAGES = ["iongji", "hoa2tai", "sandhi", "review", "worksheet"]
for _s in STUDY_PAGES:
    PAGES[f"docs/study/{_s}/index.html"] = SITE + f"study/{_s}/"


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
    """逐頁頂懸的導覽愛仝款 (目標網址佮文字攏仝), 工具、檢定下拉愛連會著逐个功能。"""
    expected = nav_targets("docs/index.html")
    urls = {url for url, _ in expected}
    for path in [
        "try/",
        "try/#practice",
        *(f"{t}/" for t in TOOL_PAGES),
        "study/",
        *(f"study/{s}/" for s in STUDY_PAGES),
    ]:
        assert SITE + path in urls, f"首頁導覽愛有 {path}"
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


def test_tool_pages_are_part_of_the_main_site():
    """轉換、詞彙、文法逐頁: canonical/og/JSON-LD 指家己, 掛佇「寫台文」網站下, sitemap 有。"""
    import json

    sitemap = (ROOT / "docs/sitemap.xml").read_text(encoding="utf-8")
    for tool in TOOL_PAGES:
        head = _Head()
        head.feed((ROOT / f"docs/{tool}/index.html").read_text(encoding="utf-8"))
        canonical = SITE + f"{tool}/"
        assert head.links["canonical"] == canonical, tool
        assert head.meta["og:url"] == canonical, tool
        assert head.meta["og:site_name"] == "寫台文 Siá Tâi-bûn", tool
        assert head.meta.get("og:image", "").startswith(SITE), tool
        assert head.h1 == 1, tool
        graph = [node for block in head.jsonld for node in json.loads(block)["@graph"]]
        page = next(n for n in graph if n["@type"] == "WebPage")
        assert page["@id"] == canonical and page["isPartOf"] == {"@id": SITE + "#website"}, tool
        assert [i["item"] for i in page["breadcrumb"]["itemListElement"]] == [SITE, canonical], tool
        assert any(n["@type"] == "WebApplication" and n["url"] == canonical for n in graph), tool
        assert f"<loc>{canonical}</loc>" in sitemap, tool
    assert "/thak/</loc>" not in sitemap, "舊入口 /thak/ 已經轉址, sitemap 毋通閣列"


def test_study_pages_sit_under_the_study_overview():
    """檢定練習逐頁: canonical 指家己, 麵包屑 寫台文 → 檢定練習 → 本頁, sitemap 有。"""
    import json

    sitemap = (ROOT / "docs/sitemap.xml").read_text(encoding="utf-8")
    assert f"<loc>{SITE}study/</loc>" in sitemap
    for s in STUDY_PAGES:
        head = _Head()
        head.feed((ROOT / f"docs/study/{s}/index.html").read_text(encoding="utf-8"))
        canonical = SITE + f"study/{s}/"
        assert head.links["canonical"] == canonical == head.meta["og:url"], s
        assert head.h1 == 1, s
        graph = [node for block in head.jsonld for node in json.loads(block)["@graph"]]
        page = next(n for n in graph if n["@type"] == "WebPage")
        crumbs = [i["item"] for i in page["breadcrumb"]["itemListElement"]]
        assert crumbs == [SITE, SITE + "study/", canonical], s
        assert f"<loc>{canonical}</loc>" in sitemap, s


def test_old_thak_entry_redirects_to_converter():
    """舊讀台文入口 (/thak/、thak.anatomind.com 轉來的) 愛 301 去轉換頁, 舊連結袂斷。"""
    rules = {
        tuple(line.split()[:3])
        for line in (ROOT / "docs/_redirects").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    for src in ("/thak", "/thak/", "/thak/index.html"):
        assert (src, "/convert/", "301") in rules, src
    assert not (ROOT / "docs/thak/index.html").exists(), "舊頁留咧會佮轉址衝突"
    for page in PAGES:
        assert "thak.anatomind.com" not in (ROOT / page).read_text(encoding="utf-8"), page


class _Assets(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "link" and a.get("rel") == "stylesheet":
            self.urls.append(a.get("href") or "")
        elif tag == "script" and a.get("src"):
            self.urls.append(a["src"])


def test_site_css_and_js_carry_a_version_query():
    """正式站 CSS/JS 快取 186 工: 本站資產網址無帶 ?v= 的話, 改版了後舊訪客會提著舊樣式
    (2026-10 導覽「工具」下拉因為按呢攏排佇導覽列頂懸)。"""
    for page in PAGES:
        parser = _Assets()
        parser.feed((ROOT / page).read_text(encoding="utf-8"))
        local = [u for u in parser.urls if not u.startswith(("http:", "https:", "//"))]
        assert local, page
        for url in local:
            assert "?v=" in url, f"{page}: {url}"


def test_study_data_files_are_not_gitignored():
    """根目錄 .gitignore 的 data/ 會吞著 docs/study/data/ (2026-10 首擺部署 JSON 全無去, 回首頁 HTML)。"""
    import subprocess

    files = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "docs/study/data").glob("*.json"))
    assert len(files) >= 3
    r = subprocess.run(["git", "check-ignore", *files], cwd=ROOT, capture_output=True, text=True)
    assert r.stdout.strip() == "", f"予 .gitignore 擋著: {r.stdout}"
