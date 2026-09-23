#!/usr/bin/env python3
"""Build PhahTaiBun-Trime.zip - a ready-to-extract Rime user-data overlay for Android frontends.

Default bundle (redistributable):
- phah_taibun core (schema/, lua/, rime.lua)
- `~` reverse-lookup closure from rime shared data: terra_pinyin dictionary plus
  bopomofo/bopomofo_tw/zhuyin, since bopomofo.schema uses terra_pinyin as its
  dictionary (there is no separate bopomofo dict upstream)

Variant bundle (--with-liur -> PhahTaiBun-Trime-liur.zip, shipped in parallel):
- adds the boshiamy (liur) closure from a rime-liur-arch checkout: same file set
  as install_windows.ps1 Step 3.5 (root files, lua/ flattened, lunar_calendar/
  subdir kept, opencc/ copied, configs/liur.schema.yaml -> liur.schema.yaml mixed)
- upstream carries no named license file; its README declares
  "本專案基於開源授權發佈". The project owner opted to redistribute it with
  LIUR-PROVENANCE.txt recording source repo, commit and that declaration;
  if the upstream ever attaches formal license terms, those take precedence.

The output zip mirrors a Rime user directory root. Entries are sorted and
timestamps fixed, so repeated builds are byte-identical (PLAN 9-3J).

Usage:
    uv run python scripts/build_trime_package.py                     # PhahTaiBun-Trime.zip
    uv run python scripts/build_trime_package.py --with-liur         # PhahTaiBun-Trime-liur.zip
    uv run python scripts/build_trime_package.py --output dist/x.zip --tree-only dist/tree
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PHAH_SCHEMA_FILES = [
    "phah_taibun.schema.yaml",
    "phah_taibun_telex.schema.yaml",
    "phah_taibun.dict.yaml",
    "hanlo_rules.yaml",
    "hoabun_map.txt",
    "lighttone_rules.json",
    "moe700.yaml",
]

REVERSE_LOOKUP_FILES = [
    "terra_pinyin.dict.yaml",
    "bopomofo.schema.yaml",
    "bopomofo_tw.schema.yaml",
    "zhuyin.yaml",
]

# LGPL-3.0 來源: 檔案 -> (專案, repo, Debian/Ubuntu 套件, 著作權人, 併入本包的說明)
REVERSE_SOURCES = {
    "bopomofo.schema.yaml": (
        "rime-bopomofo",
        "https://github.com/rime/rime-bopomofo",
        "rime-data-bopomofo",
        "GONG Chen <chen.sst@gmail.com>",
        "",
    ),
    "bopomofo_tw.schema.yaml": (
        "rime-bopomofo",
        "https://github.com/rime/rime-bopomofo",
        "rime-data-bopomofo",
        "GONG Chen <chen.sst@gmail.com>",
        "",
    ),
    "zhuyin.yaml": (
        "rime-bopomofo",
        "https://github.com/rime/rime-bopomofo",
        "rime-data-bopomofo",
        "GONG Chen <chen.sst@gmail.com>",
        "",
    ),
    "terra_pinyin.dict.yaml": (
        "rime-terra-pinyin",
        "https://github.com/rime/rime-terra-pinyin",
        "rime-data-terra-pinyin",
        "GONG Chen <chen.sst@gmail.com>, Kunki Chiu <cokunhui@gmail.com>",
        "schema data refined from Chewing (LGPL), OpenCC (Apache-2.0),"
        " Android Pinyin IME (Apache-2.0) and moedict.tw (CC0-1.0)",
    ),
}

THIRD_PARTY_NOTICE = "THIRD-PARTY-NOTICES.txt"
LICENSE_DIR = "licenses"
PROJECT_LICENSE = "LICENSE-PhahTaiBun.txt"
LICENSE_TEXTS = {
    "LGPL-3.0.txt": "LGPL-3",
    "GPL-3.0.txt": "GPL-3",
}

# 桌面前端專屬或使用者狀態檔, 不進 Android zip.
LIUR_ROOT_EXCLUDE = {
    ".gitignore",
    "README.md",
    "default.custom.yaml",
    "installation.yaml",
    "rime.lua",
    "rime_liur_installer.sh",
    "rime_liur_installer.ps1",
    "rime_liur_installer_linux.sh",
    "squirrel.custom.yaml",
    "weasel.custom.yaml",
}

LIUR_SCHEMA_SOURCE = "configs/liur.schema.yaml"
LIUR_PROVENANCE = "LIUR-PROVENANCE.txt"
RIME_LUA_MARKER = "liu_w2c_sorter"
INSTALL_DOC = "INSTALL-Trime.md"
TRIME_PATCH = "trime.custom.yaml"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def _default_custom_yaml(include_liur: bool) -> str:
    schemas = ["phah_taibun", "phah_taibun_telex"]
    if include_liur:
        schemas += ["liur", "easy_en"]
    schemas.append("bopomofo_tw")

    lines = [
        "# default.custom.yaml - 拍台文 Trime 包 (scripts/build_trime_package.py 產生)",
        "# @next 附加: 保留前端內建 default.yaml 的方案清單, 不整檔覆蓋",
        "patch:",
    ]
    for index, schema in enumerate(schemas):
        key = "schema_list/@next" if index == 0 else f"schema_list/@next {index}"
        lines += [f"  {key}:", f"    schema: {schema}"]
    lines += [
        "  switcher/save_options/@before 0: poj_mode",
        "  switcher/save_options/@next: full_romanization",
    ]
    return "\n".join(lines) + "\n"


def _merge_rime_lua(phah_lua: str, liur_lua: str) -> str:
    """拍台文註冊在前, liur 全檔附加在後; marker 已存在則不重複附加."""
    merged = phah_lua.rstrip("\n")
    if RIME_LUA_MARKER in merged:
        return merged + "\n"
    block = liur_lua.strip("\n")
    return (
        f"{merged}\n\n"
        "-- liu (rime-liur) registrations appended - same strategy as install_windows.ps1\n\n"
        f"{block}\n"
    )


def _git_value(liur_dir: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(liur_dir), *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else "unknown"


def _package_version(package: str) -> str:
    try:
        result = subprocess.run(
            ["dpkg-query", "-W", "-f=${Version}", package],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    version = result.stdout.strip()
    return version if result.returncode == 0 and version else "unknown"


def _write_third_party_notices(dest: Path, *, rime_data_dir: Path, common_licenses_dir: Path) -> None:
    """LGPL-3.0 標示義務: 完整授權全文 + 逐檔來源/著作權/雜湊.

    LGPL-3.0 以引用方式納入 GPL-3.0, 因此兩份全文都要附.
    """
    license_dir = dest / LICENSE_DIR
    license_dir.mkdir(parents=True, exist_ok=True)
    for target, source in LICENSE_TEXTS.items():
        source_path = common_licenses_dir / source
        if not source_path.is_file():
            raise SystemExit(
                f"錯誤, 找不到 {source_path}: LGPL-3.0 需要附上授權全文 (用 --common-licenses-dir 指定)"
            )
        _copy_file(source_path, license_dir / target)

    _copy_file(REPO_ROOT / "LICENSE", dest / PROJECT_LICENSE)

    lines = [
        "PhahTaiBun-Trime.zip 第三方授權標示 / third-party notices",
        "=" * 60,
        "",
        "本包含有下列專案的未修改檔案, 皆為 GNU Lesser General Public License v3.0",
        "(LGPL-3.0); 授權全文見 licenses/LGPL-3.0.txt 與 licenses/GPL-3.0.txt",
        "(LGPL-3.0 以引用方式納入 GPL-3.0, 故兩份一併附上).",
        "",
        f"檔案取自系統 rime 共享資料夾: {rime_data_dir}",
        "未做任何修改; 原始碼見下列 repository.",
        "",
    ]
    for name in REVERSE_LOOKUP_FILES:
        project, repository, package, holders, note = REVERSE_SOURCES[name]
        digest = hashlib.sha256((dest / name).read_bytes()).hexdigest()
        lines += [
            f"檔案 file      : {name}",
            f"  專案 project : {project}",
            f"  repository   : {repository}",
            f"  著作權 owners: {holders}",
            "  授權 license : LGPL-3.0",
            f"  來源 package : {package} {_package_version(package)}",
            f"  sha256       : {digest}",
        ]
        if note:
            lines.append(f"  備註 note    : {note}")
        lines.append("")

    lines += [
        "拍台文自己的檔案 (schema/phah_taibun*, lua/, rime.lua, default.custom.yaml,",
        f"INSTALL-Trime.md) 為 MIT 授權, 見 {PROJECT_LICENSE}.",
    ]
    (dest / THIRD_PARTY_NOTICE).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_liur_provenance(dest: Path, liur_dir: Path) -> None:
    """記錄 liur 來源, commit 與上游宣告, 作為隨包散布的來源標示."""
    lines = [
        "rime-liur-arch provenance / 嘸蝦米檔案集來源標示",
        "source remote: https://github.com/soanseng/rime-liur-arch",
        f"commit: {_git_value(liur_dir, 'rev-parse', 'HEAD')}",
        "",
        "upstream: ryanwuson/rime-liur (via soanseng/rime-liur-arch)",
        "license: 上游未附具名授權檔 (GitHub license API 為 null), README 僅宣告",
        "         「本專案基於開源授權發佈，歡迎使用和改進」。",  # noqa: RUF001 - 上游 README 逐字引用
        "         本專案依該宣告隨包散布並標示來源; 若上游日後補上正式授權條款,",
        "         以其條款為準。",
    ]
    (dest / LIUR_PROVENANCE).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _copy_liur(dest: Path, liur_dir: Path) -> None:
    if not liur_dir.is_dir():
        raise SystemExit(f"錯誤, 找不到 rime-liur-arch: {liur_dir} (用 --liur-dir 指定)")

    for src in sorted(liur_dir.iterdir()):
        if src.is_file() and src.name not in LIUR_ROOT_EXCLUDE:
            _copy_file(src, dest / src.name)

    lua_dir = liur_dir / "lua"
    for src in sorted(lua_dir.glob("*.lua")):
        _copy_file(src, dest / "lua" / src.name)
    lunar_dir = lua_dir / "lunar_calendar"
    if lunar_dir.is_dir():
        for src in sorted(lunar_dir.iterdir()):
            if src.is_file():
                _copy_file(src, dest / "lua" / "lunar_calendar" / src.name)

    opencc_dir = liur_dir / "opencc"
    if opencc_dir.is_dir():
        for src in sorted(opencc_dir.iterdir()):
            if src.is_file():
                _copy_file(src, dest / "opencc" / src.name)

    schema_src = liur_dir / LIUR_SCHEMA_SOURCE
    if not schema_src.is_file():
        raise SystemExit(f"錯誤, 找不到 {schema_src}")
    _copy_file(schema_src, dest / "liur.schema.yaml")

    _write_liur_provenance(dest, liur_dir)


def build_tree(
    dest: Path,
    *,
    liur_dir: Path | None,
    rime_data_dir: Path,
    common_licenses_dir: Path = Path("/usr/share/common-licenses"),
) -> Path:
    """把 overlay 檔案樹寫到 dest; liur_dir 為 None 時只打包可再散布的內容."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    for name in PHAH_SCHEMA_FILES:
        _copy_file(REPO_ROOT / "schema" / name, dest / name)

    for src in sorted((REPO_ROOT / "lua").glob("*.lua")):
        _copy_file(src, dest / "lua" / src.name)

    for name in REVERSE_LOOKUP_FILES:
        src = rime_data_dir / name
        if not src.is_file():
            raise SystemExit(f"錯誤, 找不到反查依賴 {src} (用 --rime-data-dir 指向共享資料夾)")
        _copy_file(src, dest / name)

    _write_third_party_notices(dest, rime_data_dir=rime_data_dir, common_licenses_dir=common_licenses_dir)

    rime_lua = (REPO_ROOT / "rime.lua").read_text(encoding="utf-8")
    if liur_dir is not None:
        rime_lua = _merge_rime_lua(rime_lua, (liur_dir / "rime.lua").read_text(encoding="utf-8"))
    (dest / "rime.lua").write_text(rime_lua, encoding="utf-8")

    (dest / "default.custom.yaml").write_text(_default_custom_yaml(liur_dir is not None), encoding="utf-8")
    _copy_file(REPO_ROOT / "packaging" / "android" / INSTALL_DOC, dest / INSTALL_DOC)
    _copy_file(REPO_ROOT / "packaging" / "android" / TRIME_PATCH, dest / TRIME_PATCH)

    if liur_dir is not None:
        _copy_liur(dest, liur_dir)

    return dest


def build_zip(tree: Path, output: Path) -> Path:
    """把 overlay 目錄壓成決定性 zip: 路徑排序, 固定時間戳與權限位."""
    output.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(path for path in tree.rglob("*") if path.is_file())
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            info = zipfile.ZipInfo(str(path.relative_to(tree)), date_time=ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return output


def _resolve_output(output: Path, *, with_liur: bool, is_default: bool) -> Path:
    """--with-liur 且未指定 --output 時, 輸出名稱加 -liur 後綴, 不覆蓋輕量包."""
    if with_liur and is_default:
        return output.with_name(f"{output.stem}-liur{output.suffix}")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--with-liur",
        action="store_true",
        help="加入嘸蝦米, 產出 PhahTaiBun-Trime-liur.zip (與不含嘸蝦米版並行發佈)",
    )
    parser.add_argument(
        "--liur-dir",
        type=Path,
        default=Path(os.environ.get("PHAH_TAIBUN_LIUR_DIR", Path.home() / "projects" / "rime-liur-arch")),
        help="rime-liur-arch checkout 路徑 (只在 --with-liur 時使用)",
    )
    parser.add_argument("--rime-data-dir", type=Path, default=Path("/usr/share/rime-data"))
    parser.add_argument("--common-licenses-dir", type=Path, default=Path("/usr/share/common-licenses"))
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "dist" / "PhahTaiBun-Trime.zip")
    parser.add_argument("--tree-only", type=Path, default=None, help="只產出 overlay 目錄, 不壓 zip")
    args = parser.parse_args(argv)

    liur_dir = args.liur_dir if args.with_liur else None
    output = _resolve_output(
        args.output,
        with_liur=liur_dir is not None,
        is_default=args.output == parser.get_default("output"),
    )
    if args.tree_only is not None:
        tree = build_tree(
            args.tree_only,
            liur_dir=liur_dir,
            rime_data_dir=args.rime_data_dir,
            common_licenses_dir=args.common_licenses_dir,
        )
        print(f"overlay: {tree}")
        return 0

    with tempfile.TemporaryDirectory(prefix="phah-taibun-trime-") as tmp:
        tree = build_tree(
            Path(tmp) / "overlay",
            liur_dir=liur_dir,
            rime_data_dir=args.rime_data_dir,
            common_licenses_dir=args.common_licenses_dir,
        )
        archive = build_zip(tree, output)
    print(f"zip: {archive} ({archive.stat().st_size} bytes)")
    if liur_dir is None:
        print("bundle: phah_taibun + bopomofo_tw + terra_pinyin")
    else:
        print(f"bundle: phah_taibun + bopomofo_tw + terra_pinyin + liur ({liur_dir})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
