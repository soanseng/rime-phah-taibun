#!/usr/bin/env python3
"""Generate lua/phah_taibun_emoji_menu.lua from Unicode's emoji-test.txt.

The menu groups fully-qualified emoji by Unicode's official groups (CLDR
order — the order recommended for keyboard palettes), skipping only the
"Component" group (modifier bases, not standalone emoji). Skin-tone and
ZWJ sequences are included; the menu paginates.

Source: https://unicode.org/Public/emoji/15.1/emoji-test.txt (Unicode License).
Usage:
    uv run python scripts/build_emoji_categories.py --input data/emoji-test.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "lua" / "phah_taibun_emoji_menu.lua"

# Unicode group -> Chinese display name (menu order follows the file).
GROUP_NAMES = {
    "Smileys & Emotion": "笑臉與情感",
    "People & Body": "人與身體",
    "Animals & Nature": "動物與自然",
    "Food & Drink": "食物與飲料",
    "Travel & Places": "旅行與地點",
    "Activities": "活動",
    "Objects": "物件",
    "Symbols": "符號",
    "Flags": "旗幟",
}


def strip_version_token(display: str) -> str:
    """Remove a leading 'E1.0'-style emoji-version token from a name."""
    token, _, rest = display.partition(" ")
    if token.startswith("E") and token[1:].replace(".", "").isdigit() and rest:
        return rest
    return display


def parse_emoji_test(path: Path) -> list[tuple[str, list[tuple[str, str]]]]:
    groups: list[tuple[str, list[tuple[str, str]]]] = []
    current: tuple[str, list[tuple[str, str]]] | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("# group:"):
            name = raw.split(":", 1)[1].strip()
            if name in GROUP_NAMES:
                current = (name, [])
                groups.append(current)
            else:
                current = None  # skip Component / anything unmapped
            continue
        if raw.startswith("#") or ";" not in raw:
            continue
        if current is None:
            continue
        _, right = raw.split(";", 1)
        status = right.split("#", 1)[0].strip()
        if status != "fully-qualified":
            continue
        # Line format: "1F600 ; fully-qualified # 😀 grinning face" —
        # the emoji glyph is the first token of the comment, not the
        # codepoint column on the left.
        comment = right.split("#", 1)[1].strip() if "#" in right else ""
        parts = comment.split(None, 1)
        if not parts:
            continue
        emoji = parts[0]
        display = parts[1].strip() if len(parts) > 1 else ""
        # Drop the "E1.0"-style version token that precedes the name.
        display = strip_version_token(display)
        current[1].append((emoji, display))
    return groups


def lua_quote(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, required=True, help="path to emoji-test.txt"
    )
    parser.add_argument("--version", default="15.1", help="emoji-test.txt version")
    args = parser.parse_args()

    groups = parse_emoji_test(args.input)
    if not groups:
        print("error: no groups parsed", file=sys.stderr)
        return 1

    lines = [
        "-- phah_taibun_emoji_menu.lua",
        "-- `e Emoji 分類選單: `e 開目錄, `eN 直達第 N 群 (Unicode 官方分群,",
        "-- CLDR 鍵盤建議順序; 全收 fully-qualified (含膚色與 ZWJ 序列), 略過 Component 群.",
        f"-- 資料來源: Unicode emoji-test.txt {args.version}.",
        "--",
        "-- UNICODE LICENSE V3",
        "--",
        "-- COPYRIGHT AND PERMISSION NOTICE",
        "--",
        "-- Copyright © 1991-2026 Unicode, Inc.",
        "--",
        "-- NOTICE TO USER: Carefully read the following legal agreement. BY",
        "-- DOWNLOADING, INSTALLING, COPYING OR OTHERWISE USING DATA FILES, AND/OR",
        "-- SOFTWARE, YOU UNEQUIVOCALLY ACCEPT, AND AGREE TO BE BOUND BY, ALL OF THE",
        "-- TERMS AND CONDITIONS OF THIS AGREEMENT. IF YOU DO NOT AGREE, DO NOT",
        "-- DOWNLOAD, INSTALL, COPY, DISTRIBUTE OR USE THE DATA FILES OR SOFTWARE.",
        "--",
        "-- Permission is hereby granted, free of charge, to any person obtaining a",
        "-- copy of data files and any associated documentation (the \"Data Files\") or",
        "-- software and any associated documentation (the \"Software\") to deal in",
        "-- the Data Files or Software without restriction, including without limitation",
        "-- the rights to use, copy, modify, merge, publish, distribute, and/or sell",
        "-- copies of the Data Files or Software, and to permit persons to whom the",
        "-- Data Files or Software are furnished to do so, provided that either (a) this",
        "-- copyright and permission notice appear with all copies of the Data Files or",
        "-- Software, or (b) this copyright and permission notice appear in associated",
        "-- Documentation.",
        "--",
        "-- THE DATA FILES AND SOFTWARE ARE PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY",
        "-- KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF",
        "-- MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT OF",
        "-- THIRD PARTY RIGHTS.",
        "--",
        "-- IN NO EVENT SHALL THE COPYRIGHT HOLDER OR HOLDERS INCLUDED IN THIS NOTICE",
        "-- BE LIABLE FOR ANY CLAIM, OR ANY SPECIAL INDIRECT OR CONSEQUENTIAL DAMAGES,",
        "-- OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,",
        "-- WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION,",
        "-- ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THE DATA",
        "-- FILES OR SOFTWARE.",
        "--",
        "-- Except as contained in this notice, the name of a copyright holder shall",
        "-- not be used in advertising or otherwise to promote the sale, use or other",
        "-- dealings in these Data Files or Software without prior written",
        "-- authorization of the copyright holder.",
        "-- Full terms: https://www.unicode.org/license.txt",
        "-- 本檔由 scripts/build_emoji_categories.py 產生; 修改資料請改 generator",
        "-- 重跑, 勿直接手改.",
        "local M = {}",
        "",
        "local GROUPS = {",
    ]
    for idx, (name, emojis) in enumerate(groups, start=1):
        lines.append(f"  {{ key = {lua_quote(str(idx))}, name = {lua_quote(GROUP_NAMES[name])}, emojis = {{")
        for emoji, display in emojis:
            lines.append(f"    {{{lua_quote(emoji)}, {lua_quote(display)}}},")
        lines.append("  } },")
    lines.append("}")
    lines.append(
        """
function M.func(input, seg, env)
  if not input:match("^`") then
    return
  end
  local code = input:gsub("^`", ""):gsub("`$", "")

  if code == "e" then
    for _, g in ipairs(GROUPS) do
      local label = string.format("e%s %s (%d)", g.key, g.name, #g.emojis)
      yield(Candidate("emoji_menu", seg.start, seg._end, label, "Emoji"))
    end
    return
  end

  local k = code:match("^e([1-9])$")
  if not k then
    return
  end
  for _, g in ipairs(GROUPS) do
    if g.key == k then
      for _, e in ipairs(g.emojis) do
        yield(Candidate("emoji_menu", seg.start, seg._end, e[1], e[2]))
      end
      return
    end
  end
end

return M
"""
    )
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    total = sum(len(emojis) for _, emojis in groups)
    print(f"wrote {OUTPUT} ({len(groups)} groups, {total} emoji)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
