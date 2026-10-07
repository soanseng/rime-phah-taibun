"""Web playground (docs/try/) bundle rules.

The playground runs the real schemas in a wasm librime, but ships a concise
dictionary and no desktop-only closures. These tests pin what makes it a
faithful miniature of 寫台文: word identity, real weights (長詞不敗 survives
the cut) and engine component lists that only reference shipped data.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts.build_web_playground import (
    PACK_DIR,
    SCHEMAS,
    WEB_DROP,
    public_pairs,
    select_web_entries,
    web_custom_yaml,
)

ROOT = Path(__file__).parents[1]


def test_selection_keeps_word_identity_per_reading():
    """重/tîng 與 重/tāng 是兩個詞: 公開詞庫只收其中一讀時, 另一讀不得混進來。"""
    main = {("重陽", "tiong5 iong5"): 9000, ("重量", "tang7 liong7"): 8000, ("重量", "tiong7 liong7"): 7000}
    public = {("重陽", "tiong5 iong5"), ("重量", "tang7 liong7")}
    got = {(t, r) for t, r, _ in select_web_entries(main, public, word_limit=10, single_min=1000)}
    assert got == {("重陽", "tiong5 iong5"), ("重量", "tang7 liong7")}


def test_selection_ranks_words_by_main_weight_and_copies_it_unchanged():
    """取主字典權重最高的 N 詞, 權重原樣 — 整詞 >= K x 拆分和 的不變量才延續到子集。"""
    main = {("食飯", "tsiah8 png7"): 9000, ("食飽", "tsiah8 pa2"): 5000, ("食物", "sit8 but8"): 7000}
    public = set(main)
    got = select_web_entries(main, public, word_limit=2, single_min=1000)
    assert got == [("食飯", "tsiah8 png7", 9000), ("食物", "sit8 but8", 7000)]


def test_selection_adds_main_singles_above_threshold_regardless_of_public_lexicon():
    """單字是逐音節組句的底: 公開詞庫無收的常用單字也愛在。"""
    main = {("食", "tsiah8"): 3000, ("𤆬", "tshua7"): 1200, ("罕", "han2"): 999, ("食飯", "tsiah8 png7"): 9000}
    got = select_web_entries(main, {("食飯", "tsiah8 png7")}, word_limit=10, single_min=1000)
    assert [e[0] for e in got] == ["食飯", "食", "𤆬"]


def test_default_selection_keeps_everyday_function_word_readings():
    """預設門檻愛收著日常虛詞白讀 (主字典權重 500-1000): 欠 欲/beh4 時
    「這馬欲去」會組做「這馬袂曉…」。"""
    main = {("欲", "beh4"): 800, ("咧", "leh4"): 640, ("阮", "gun2"): 565, ("𠕇", "ting7"): 120}
    got = {(t, r) for t, r, _ in select_web_entries(main, set())}
    assert got == {("欲", "beh4"), ("咧", "leh4"), ("阮", "gun2")}


def test_selection_keeps_corpus_attested_everyday_words_over_heavier_unattested_ones():
    """主字典權重為長詞不敗刻意抬長詞 (食飯 3591 < 罕用三字詞 9000);
    名額有限時, 語料有出現的日常詞愛先入選, 權重照原樣不改。"""
    main = {("食飯", "tsiah8 png7"): 3591, ("鹹酸甜", "kiam5 sng1 tinn1"): 9000}
    got = select_web_entries(main, set(main), attested={("食飯", "tsiah8 png7"): 29}, word_limit=1, single_min=1000)
    assert got == [("食飯", "tsiah8 png7", 3591)]


def test_public_pairs_normalizes_reading_whitespace():
    """讀台文詞庫有雙空白讀音 (ku2 ku2  a2), 對主字典鍵前愛正規化。"""
    assert public_pairs({"久久仔": {"r": ["ku2 ku2  a2"]}}) == {("久久仔", "ku2 ku2 a2")}


def test_web_patch_drops_unshipped_components_and_keeps_the_rest_in_order():
    """每個方案的 translators/filters 只刪網頁無資料的元件, 其餘順序照原方案。"""
    for schema in SCHEMAS:
        text = (ROOT / "schema" / f"{schema}.schema.yaml").read_text(encoding="utf-8")
        engine = yaml.safe_load(text)["engine"]
        patch = yaml.safe_load(web_custom_yaml(text))["patch"]
        for kind in ("translators", "filters"):
            expected = [c for c in engine[kind] if c not in WEB_DROP]
            assert patch[f"engine/{kind}"] == expected, (schema, kind)
            assert not set(patch[f"engine/{kind}"]) & WEB_DROP


def test_web_patch_references_only_shipped_lua_modules():
    """改名或新增 Lua 模組時, 網頁版袂使引用無出貨的模組 (部署會失敗、候選全無)."""
    from scripts.build_web_playground import LUA_EXCLUDE

    shipped = {p.stem for p in (ROOT / "lua").glob("*.lua") if p.name not in LUA_EXCLUDE}
    for schema in SCHEMAS:
        text = (ROOT / "schema" / f"{schema}.schema.yaml").read_text(encoding="utf-8")
        patch = yaml.safe_load(web_custom_yaml(text))["patch"]
        processors = yaml.safe_load(text)["engine"]["processors"]
        for comp in [*patch["engine/translators"], *patch["engine/filters"], *processors]:
            if comp.startswith("lua_") and "@*" in comp:
                assert comp.split("@*", 1)[1] in shipped, (schema, comp)


# Lua 開的資料檔中, 網頁版刻意無出貨的: 值是理由
WEB_OMITTED_DATA = {
    "hoabun_map.txt": "華→台對照只供注音反查(網頁無)與同音選字後備, 2 MB",
    "phah_taibun_learning.tsv": "執行時寫入的使用者學習紀錄, 毋是出貨資料",
}


def test_bundle_ships_every_data_file_the_lua_modules_open():
    """Lua 用檔名開的資料檔攏愛佇 docs/try 包內 (除了明列理由的)。

    欠 phah_taibun.wordlist 時, 全羅整句會退做逐字空白、無詞內連字號 —
    無錯誤訊息, 只是輸出靜靜仔變款。
    """
    import json
    import re

    opened = set()
    for lua in (ROOT / "lua").glob("*.lua"):
        opened |= set(re.findall(r'"/?([a-z_0-9]+\.(?:yaml|json|txt|wordlist|tsv))"', lua.read_text(encoding="utf-8")))
    shipped = set(json.loads((ROOT / "docs" / "try" / "manifest.json").read_text(encoding="utf-8"))["files"])
    assert opened - shipped - set(WEB_OMITTED_DATA) == set()


def test_bundle_files_are_not_gitignored():
    """manifest 列的檔案攏愛會使 commit: Cloudflare 對 git 部署,
    被 .gitignore 食去的檔案佇正式站會變做首頁 HTML 回退 (曾因 data/ 規則整包消失)。"""
    import json
    import subprocess

    manifest = json.loads((ROOT / "docs" / "try" / "manifest.json").read_text(encoding="utf-8"))
    paths = [f"docs/try/{PACK_DIR}/{name}" for name in manifest["files"]]
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", *paths], cwd=ROOT, capture_output=True, text=True, check=False
    )
    assert result.stdout.split() == []
