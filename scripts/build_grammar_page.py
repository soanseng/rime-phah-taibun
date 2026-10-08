"""文法筆記 (grammar-notes.json) → docs/grammar/index.html 靜態 HTML.

筆記直接寫佇 HTML: 搜尋引擎免跑 JS 就讀會著, 頁面嘛免等 JSON 才有內容 (LCP).
改 docs/thak/data-public/grammar-notes.json 了後愛重跑:

    uv run python scripts/build_grammar_page.py          # 寫入 HTML
    uv run python scripts/build_grammar_page.py --check  # 檢查仝步 (測試用)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTES = ROOT / "docs" / "thak" / "data-public" / "grammar-notes.json"
PAGE = ROOT / "docs" / "grammar" / "index.html"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")


def render_cats(data: dict) -> str:
    buttons = [f'<button type="button" class="seg-btn is-active" data-cat="">全部（{len(data["notes"])}）</button>']  # noqa: RUF001 - 台文介面用全形括號
    buttons += [
        f'<button type="button" class="seg-btn" data-cat="{esc(c["id"])}">{esc(c["title"])}</button>'
        for c in data["categories"]
    ]
    return "".join(buttons)


def render_note(n: dict, cat_title: dict[str, str]) -> str:
    # body 段落是本站自寫的 HTML (有 <b> 等), 照原樣
    body = "".join(f"<p>{p}</p>" for p in n["body"])
    exs = []
    for e in n["examples"]:
        hua = f'<span class="hua">　{esc(e["hua"])}</span>' if e.get("hua") else ""
        note = f'<span class="hua">　〔註〕{esc(e["note"])}</span>' if e.get("note") else ""  # noqa: RUF001 - 台文介面用全形括號
        src = "教典" if e.get("src") == "moedict" else "自造"
        exs.append(
            f'<div class="gr-ex"><span class="han">{esc(e["han"])}</span>'
            f'<span class="tl">　{esc(e["tl"])}</span>{hua}{note}'
            f'<span class="gr-src-tag">{src}</span></div>'
        )
    refs = "・".join(
        f'<a href="{esc(r["url"])}" target="_blank" rel="noopener">{esc(r["label"])}</a>' for r in n["refs"]
    )
    return (
        f'<article class="gr-note" id="note-{esc(n["id"])}" data-cat="{esc(n["cat"])}">'
        f'<span class="gr-cat">{esc(cat_title.get(n["cat"], ""))}</span>'
        f"<h3>{esc(n['title'])}</h3>{body}"
        f'<div class="gr-ex-list">{"".join(exs)}</div>'
        f'<p class="gr-refs hint">參考：{refs}</p>'  # noqa: RUF001 - 台文介面用全形冒號
        "</article>"
    )


def render_notes(data: dict) -> str:
    cat_title = {c["id"]: c["title"] for c in data["categories"]}
    return "\n".join(render_note(n, cat_title) for n in data["notes"])


def fill(html: str, name: str, content: str) -> str:
    pattern = re.compile(rf"(<!-- {name}:begin -->).*?(<!-- {name}:end -->)", re.S)
    if not pattern.search(html):
        raise SystemExit(f"{PAGE}: 揣無 <!-- {name}:begin/end --> 標記")
    return pattern.sub(lambda m: f"{m.group(1)}\n{content}\n{m.group(2)}", html, count=1)


def build(html: str, data: dict) -> str:
    html = fill(html, "grammar-cats", render_cats(data))
    return fill(html, "grammar-notes", render_notes(data))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="只檢查 HTML 佮 JSON 仝步, 無寫入")
    args = ap.parse_args()
    data = json.loads(NOTES.read_text(encoding="utf-8"))
    html = PAGE.read_text(encoding="utf-8")
    out = build(html, data)
    if args.check:
        if out != html:
            print(f"{PAGE.relative_to(ROOT)} 佮 grammar-notes.json 無仝步: 跑 scripts/build_grammar_page.py")
            return 1
        return 0
    PAGE.write_text(out, encoding="utf-8")
    print(f"寫入 {len(data['notes'])} 篇筆記 → {PAGE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
