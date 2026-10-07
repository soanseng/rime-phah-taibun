#!/usr/bin/env python3
"""Build docs/try/ - 寫台文網頁試打 (browser playground) data bundle.

Engine: My RIME (LibreService/my_rime, AGPL-3.0-or-later) - librime 1.8.5 +
librime-lua compiled to WebAssembly. Its dist files are vendored once into
docs/try/ (``--my-rime-dist``); worker.js is patched only to load rime.js from
the same origin instead of jsDelivr.

Data (docs/try/<PACK_DIR>/, listed in docs/try/manifest.json):
- schema/lua/rule files from this repo for phah_taibun and phah_taibun_telex,
  minus desktop-only closures (注音反查 terra_pinyin/bopomofo, emoji opencc,
  rime.lua - the wasm librime-lua supports ``@*`` module loading)
- <schema>.custom.yaml: each schema's own engine lists with the components
  whose data is not shipped removed (WEB_DROP)
- default.yaml: the engine's built-in default.yaml with schema_list reduced to
  the two schemas (a user default.custom.yaml cannot patch it: the built-in one
  lives prebuilt in shared/build/)
- phah_taibun.dict.yaml: concise web dictionary. Words = (漢字, TL) pairs of the
  讀台文 public lexicon (docs/thak/data-public/dict.json: redistributable
  layers only), corpus-attested pairs first (iCorpus identity + 楊允言 reading
  counts from data/, selection signal only), then by main weight; plus the
  main dictionary's single characters (weight >= SINGLE_MIN) so any sentence
  can still be composed syllable by syllable. Weights are copied unchanged, so
  the 長詞不敗 invariant of the main dictionary holds for the subset.

Usage:
    uv run python scripts/build_web_playground.py \
        [--public-dict docs/thak/data-public/dict.json] \
        [--my-rime-dist /path/to/@libreservice/my-rime/dist]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

import yaml

try:
    from scripts.build_wordlist import generate_wordlist
except ModuleNotFoundError:
    from build_wordlist import generate_wordlist

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "docs" / "try"
# 唔通叫 data: .gitignore 的 data/ 規則會共伊食去, 正式站 (Git 部署) 就無檔案
PACK_DIR = "pack"
DEFAULT_PUBLIC_DICT = REPO_ROOT / "docs" / "thak" / "data-public" / "dict.json"

WORD_LIMIT = 45000
# 單字是逐音節組句的底: 500 收著日常虛詞白讀 (欲 beh4 800、咧 leh4 640、阮 gun2 565)
SINGLE_MIN = 500

SCHEMAS = ["phah_taibun", "phah_taibun_telex"]
SCHEMA_FILES = [f"{s}.schema.yaml" for s in SCHEMAS] + ["hanlo_rules.yaml", "lighttone_rules.json", "moe700.yaml"]
# 網頁版無資料的元件: 注音反查(terra_pinyin)、emoji(opencc)、造詞(使用者 custom_phrase)
WEB_DROP = {
    "reverse_lookup_translator",
    "table_translator@custom_phrase",
    "lua_translator@*phah_taibun_emoji_menu",
    "reverse_lookup_filter@phah_taibun_reverse_lookup",
    "lua_filter@*phah_taibun_reverse_format",
    "simplifier@emoji_conversion",
}
LUA_EXCLUDE = {"phah_taibun_emoji_menu.lua", "phah_taibun_reverse_format.lua"}

ENGINE_FILES = ["rime.js", "rime.wasm", "rime.data", "worker.js"]
MY_RIME_CDN = re.compile(r"https://cdn\.jsdelivr\.net/npm/@libreservice/my-rime@[^/]+/dist/")


def read_dict(path: Path) -> tuple[str, dict[tuple[str, str], int]]:
    """Return (yaml header incl. '...', {(text, reading): max weight})."""
    header, sep, body = path.read_text(encoding="utf-8").partition("\n...\n")
    if not sep:
        raise SystemExit(f"錯誤, {path} 缺 YAML 結尾 '...'")
    entries: dict[tuple[str, str], int] = {}
    for line in body.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        key = (parts[0], parts[1])
        entries[key] = max(int(parts[2]), entries.get(key, 0))
    return header + "\n...\n", entries


def public_pairs(dict_json: dict) -> set[tuple[str, str]]:
    """讀台文 dict.json {text: {"r": [readings]}} to {(text, normalized reading)}."""
    return {(text, " ".join(reading.split())) for text, entry in dict_json.items() for reading in entry.get("r", [])}


def select_web_entries(
    main: dict[tuple[str, str], int],
    public: set[tuple[str, str]],
    attested: dict[tuple[str, str], int] | None = None,
    word_limit: int = WORD_LIMIT,
    single_min: int = SINGLE_MIN,
) -> list[tuple[str, str, int]]:
    """Concise dictionary: public multi-char words + main singles, main weights unchanged.

    Word slots go first to corpus-attested pairs (``attested``: corpus count,
    desc), then by main weight desc. Main weights deliberately inflate long
    words (長詞不敗), so ranking by weight alone would drop everyday words
    (食飯 3591) for rare compounds. 詞身份 = (漢字, 讀音): everything is per pair.
    Output sorted by weight desc, then text/reading for byte-stable builds.
    """
    attested = attested or {}
    words = sorted(
        (
            (text, reading, weight)
            for (text, reading), weight in main.items()
            if len(text) > 1 and (text, reading) in public
        ),
        key=lambda e: (-attested.get((e[0], e[1]), 0), -e[2], e[0], e[1]),
    )[:word_limit]
    singles = [
        (text, reading, weight) for (text, reading), weight in main.items() if len(text) == 1 and weight >= single_min
    ]
    return sorted(words + singles, key=lambda e: (-e[2], e[0], e[1]))


def corpus_counts(pairs: set[tuple[str, str]], identity_freq: Path, reading_freq: Path) -> dict[tuple[str, str], int]:
    """(漢字, TL) corpus count = identity count (iCorpus) + count of its reading (楊允言).

    Selection signal only - no corpus data is shipped. Both files are build
    outputs of scripts/build_all.py (data/, hyphenated TL). Zero counts omitted.
    """
    identity: dict[tuple[str, str], int] = {}
    for line in identity_freq.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            key = (parts[0], parts[1].replace("-", " "))
            identity[key] = identity.get(key, 0) + int(parts[2])
    by_reading: dict[str, int] = {}
    for line in reading_freq.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) == 2:
            reading = parts[0].replace("-", " ")
            by_reading[reading] = by_reading.get(reading, 0) + int(parts[1])
    counts = {pair: identity.get(pair, 0) + by_reading.get(pair[1], 0) for pair in pairs}
    return {pair: n for pair, n in counts.items() if n}


def web_custom_yaml(schema_text: str) -> str:
    """<schema>.custom.yaml: the schema's translators/filters minus WEB_DROP."""
    engine = yaml.safe_load(schema_text)["engine"]
    patch = {f"engine/{kind}": [c for c in engine[kind] if c not in WEB_DROP] for kind in ("translators", "filters")}
    head = "# 網頁試打精簡版 (scripts/build_web_playground.py 產生): 移除注音反查、emoji、造詞元件\n"
    return head + yaml.safe_dump({"patch": patch}, allow_unicode=True, sort_keys=False)


def web_default_yaml(builtin_default: str) -> str:
    """Engine built-in default.yaml with schema_list = SCHEMAS."""
    config = yaml.safe_load(builtin_default)
    config.pop("__build_info", None)
    config["schema_list"] = [{"schema": s} for s in SCHEMAS]
    config["switcher"]["save_options"] = ["full_romanization", "poj_mode", "hanlo_manual"]
    head = (
        "# default.yaml - 網頁試打版 (scripts/build_web_playground.py 產生): My RIME 內建 default.yaml 改 schema_list\n"
    )
    return head + yaml.safe_dump(config, allow_unicode=True, sort_keys=False)


def extract_builtin_default(engine_dir: Path) -> str:
    """Read /usr/share/rime-data/build/default.yaml out of rime.data via rime.js offsets."""
    loader = (engine_dir / "rime.js").read_text(encoding="utf-8")
    match = re.search(r'\{filename:"/usr/share/rime-data/build/default\.yaml",start:(\d+),end:(\d+)', loader)
    if not match:
        raise SystemExit("錯誤, rime.js 找不到內建 default.yaml 位置")
    data = (engine_dir / "rime.data").read_bytes()
    return data[int(match.group(1)) : int(match.group(2))].decode("utf-8")


def vendor_engine(dist: Path, out: Path) -> None:
    for name in ENGINE_FILES:
        src = dist / name
        if not src.is_file():
            raise SystemExit(f"錯誤, 找不到 My RIME 檔案 {src}")
        shutil.copyfile(src, out / name)
    worker = (out / "worker.js").read_text(encoding="utf-8")
    patched, count = MY_RIME_CDN.subn("./", worker)
    if count != 1:
        raise SystemExit(f"錯誤, worker.js CDN 網址應出現 1 次, 實得 {count}")
    (out / "worker.js").write_text(patched, encoding="utf-8")
    license_src = dist.parent / "LICENSE"
    if license_src.is_file():
        shutil.copyfile(license_src, out / "LICENSE-my-rime.txt")


def build(out: Path, public_dict: Path, my_rime_dist: Path | None, corpus_freq: tuple[Path, Path]) -> list[str]:
    out.mkdir(parents=True, exist_ok=True)
    if my_rime_dist is not None:
        vendor_engine(my_rime_dist, out)
    for name in ENGINE_FILES:
        if not (out / name).is_file():
            raise SystemExit(f"錯誤, {out / name} 不存在; 第一次請加 --my-rime-dist")

    data = out / PACK_DIR
    if data.exists():
        shutil.rmtree(data)
    (data / "lua").mkdir(parents=True)

    for name in SCHEMA_FILES:
        shutil.copyfile(REPO_ROOT / "schema" / name, data / name)
    for schema in SCHEMAS:
        text = (REPO_ROOT / "schema" / f"{schema}.schema.yaml").read_text(encoding="utf-8")
        (data / f"{schema}.custom.yaml").write_text(web_custom_yaml(text), encoding="utf-8")
    for src in sorted((REPO_ROOT / "lua").glob("*.lua")):
        if src.name not in LUA_EXCLUDE:
            shutil.copyfile(src, data / "lua" / src.name)
    (data / "default.yaml").write_text(web_default_yaml(extract_builtin_default(out)), encoding="utf-8")

    header, main_entries = read_dict(REPO_ROOT / "schema" / "phah_taibun.dict.yaml")
    public = public_pairs(json.loads(public_dict.read_text(encoding="utf-8")))
    attested = corpus_counts(public, *corpus_freq)
    with (data / "phah_taibun.dict.yaml").open("w", encoding="utf-8") as f:
        f.write("# 網頁精簡字典 (scripts/build_web_playground.py 產生): 讀台文公開詞庫 x 主字典權重 + 主字典單字\n")
        f.write(header)
        for text, reading, weight in select_web_entries(main_entries, public, attested):
            f.write(f"{text}\t{reading}\t{weight}\n")
    # 全羅整句分詞 (phah_taibun_data.wordlist_codes): 對網頁字典產生, 詞界與候選一致
    generate_wordlist(data / "phah_taibun.dict.yaml", data / "phah_taibun.wordlist")

    files = sorted(str(p.relative_to(data)) for p in data.rglob("*") if p.is_file())
    # version = 全部資料內容雜湊: 前端比對 IndexedDB 快取, 字典/Lua 一改就重新部署
    digest = hashlib.sha256()
    for name in files:
        digest.update(name.encode() + b"\0" + (data / name).read_bytes() + b"\0")
    manifest = {"version": digest.hexdigest()[:16], "dir": PACK_DIR, "files": files}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--public-dict", type=Path, default=DEFAULT_PUBLIC_DICT, help="讀台文 data-public/dict.json")
    parser.add_argument("--my-rime-dist", type=Path, default=None, help="@libreservice/my-rime dist/ (vendor engine)")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data", help="build_all.py 詞頻輸出目錄")
    parser.add_argument("--output", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)
    if not args.public_dict.is_file():
        raise SystemExit(f"錯誤, 找不到讀台文公開詞庫 {args.public_dict} (用 --public-dict 指定)")
    corpus_freq = (args.data_dir / "identity_freq.tsv", args.data_dir / "ungian_freq.tsv")
    for path in corpus_freq:
        if not path.is_file():
            raise SystemExit(f"錯誤, 找不到詞頻 {path} (先跑 scripts/build_all.py)")
    files = build(args.output, args.public_dict, args.my_rime_dist, corpus_freq)
    size = sum((args.output / PACK_DIR / f).stat().st_size for f in files)
    print(f"{args.output}: {len(files)} data files, {size // 1024} KiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
