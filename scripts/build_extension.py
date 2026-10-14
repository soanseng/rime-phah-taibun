#!/usr/bin/env python3
"""寫台文瀏覽器擴充功能(Chrome MV3 + Firefox MV2)一鍵打包。

依賴 docs/try/(scripts/build_web_playground.py 的產出):
- 引擎 rime.js / rime.wasm / rime.data / worker.js + LICENSE-my-rime.txt
- pack manifest(docs/try/manifest.json) -> 包內改名 pack-manifest.json(避免佮擴充功能 manifest 相硩)
- pack/(方案, 字典, Lua, 規則)

產出(--output, 預設 dist/extension):
- chrome/, firefox/ 兩个可載入目錄
- phah-taibun-chrome-<version>.zip, phah-taibun-firefox-<version>.zip(店面上傳用)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "extension"
TRY_DIR = REPO_ROOT / "docs" / "try"
ENGINE_FILES = ["rime.js", "rime.wasm", "rime.data", "worker.js", "LICENSE-my-rime.txt"]
TARGETS = {
    "chrome": {"exclude": {"background.html"}},
    "firefox": {"exclude": {"offscreen.html", "offscreen-bridge.js"}},
}


def read_version() -> str:
    # tomllib 是 3.11+; 專案愛支援 3.10 → 用 regex 讀 [project] version(pyproject 內唯一佇行頭的 version =)
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version = "([^"]+)"', text, re.M)
    if not m:
        raise SystemExit("錯誤: pyproject.toml 讀袂著 version")
    version = m.group(1)
    if not re.fullmatch(r"\d+\.\d+\.\d+(\.\d+)?", version):
        raise SystemExit(f"錯誤: pyproject 版本 {version} 毋是純數字, 商店袂接受")
    return version


def build_target(target: str, version: str, out_root: Path) -> Path:
    out = out_root / target
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # 1) extension/ 原始碼(manifest 待注入, 對向袂用著的檔案除外)
    exclude = {"manifest.chrome.json", "manifest.firefox.json"} | TARGETS[target]["exclude"]
    for p in sorted(SRC_DIR.rglob("*")):
        if p.is_file():
            rel = p.relative_to(SRC_DIR)
            if rel.parts[0] not in exclude:
                dest = out / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dest)

    # 2) manifest: 注入版本
    manifest = json.loads((SRC_DIR / f"manifest.{target}.json").read_text(encoding="utf-8"))
    manifest["version"] = version
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 3) 引擎 + pack(對 docs/try)
    missing = [f for f in ENGINE_FILES if not (TRY_DIR / f).is_file()]
    pack_manifest_path = TRY_DIR / "manifest.json"
    if not pack_manifest_path.is_file():
        missing.append("manifest.json")
    if missing:
        raise SystemExit(f"錯誤: docs/try 缺 {', '.join(missing)} - 先跑 uv run python scripts/build_web_playground.py")
    for f in ENGINE_FILES:
        shutil.copy2(TRY_DIR / f, out / f)
    pack_manifest = json.loads(pack_manifest_path.read_text(encoding="utf-8"))
    shutil.copy2(pack_manifest_path, out / "pack-manifest.json")
    pack_dir = TRY_DIR / pack_manifest["dir"]
    for f in pack_manifest["files"]:
        src = pack_dir / f
        if not src.is_file():
            raise SystemExit(f"錯誤: pack 檔案 {f} 無佇 {pack_dir} - 重跑 build_web_playground.py")
        dest = out / pack_manifest["dir"] / f
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    # 4) zip(檔案佇根, 照路徑排序 = deterministic)
    zpath = out_root / f"phah-taibun-{target}-{version}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(out.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(out).as_posix())
    return zpath


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--output", type=Path, default=REPO_ROOT / "dist" / "extension", help="輸出目錄(預設 dist/extension)"
    )
    args = parser.parse_args(argv)
    version = read_version()
    args.output.mkdir(parents=True, exist_ok=True)
    for target in TARGETS:
        zpath = build_target(target, version, args.output)
        size = zpath.stat().st_size / (1024 * 1024)
        print(f"{target}: {zpath}({size:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
