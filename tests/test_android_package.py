"""PhahTaiBun-Trime.zip: Trime overlay 打包測試.

build_trime_package.py 產出兩種可下載的 overlay, 讓使用者選擇:
  PhahTaiBun-Trime.zip      = 拍台文核心 + 注音 bopomofo_tw (兼 `~` 反查)
  PhahTaiBun-Trime-liur.zip = 再加嘸蝦米 (rime-liur-arch, 附 LIUR-PROVENANCE.txt)
授權對照: 拍台文 MIT; terra_pinyin / bopomofo / zhuyin LGPL (rime/rime-terra-pinyin, rime/rime-bopomofo);
嘸蝦米上游無具名授權檔, 依其 README「基於開源授權發佈」宣告隨包散布並標示來源.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
LIUR_DIR = Path.home() / "projects" / "rime-liur-arch"
RIME_DATA = Path("/usr/share/rime-data")

REQUIRED_PHAH = [
    "phah_taibun.schema.yaml",
    "phah_taibun_telex.schema.yaml",
    "phah_taibun.dict.yaml",
    "hanlo_rules.yaml",
    "hoabun_map.txt",
    "lighttone_rules.json",
    "moe700.yaml",
]

# `~` 注音反查閉包: phah_taibun.dependencies 有 bopomofo_tw,
# bopomofo_tw __include bopomofo.schema, 其 speller 引 zhuyin:/,
# dictionary 就是 terra_pinyin (bopomofo 沒有自己的 dict).
REQUIRED_REVERSE = [
    "terra_pinyin.dict.yaml",
    "bopomofo.schema.yaml",
    "bopomofo_tw.schema.yaml",
    "zhuyin.yaml",
]

REQUIRED_LIUR = [
    "liur.schema.yaml",
    "liur.custom.yaml",
    "liur.extended.dict.yaml",
    "phrases.chtp.dict.yaml",
    "openxiami_TCJP.dict.yaml",
    "openxiami_TradExt.dict.yaml",
    "easy_en.schema.yaml",
    "easy_en.dict.yaml",
    "allbpm.schema.yaml",
    "allbpm.dict.yaml",
    "Mount_bopomo.schema.yaml",
    "Mount_bopomo.extended.dict.yaml",
    "liur_symbols.schema.yaml",
    "liur_symbols.dict.yaml",
    "terra_pinyin_onion.schema.yaml",
    "terra_pinyin_onion.dict.yaml",
    "essay-zh-hant-onion.txt",
]

# 桌面專屬或使用者狀態檔不得進 zip (Android 端無用, 或會破壞 Trime 狀態).
FORBIDDEN_NAMES = {
    "installation.yaml",
    "weasel.custom.yaml",
    "squirrel.custom.yaml",
    "rime_liur_installer.sh",
    "rime_liur_installer.ps1",
    "rime_liur_installer_linux.sh",
    "README.md",
    "default.yaml",
    "configs",
    "fonts",
    "docs",
}

INSTALL_NAME = "INSTALL-Trime.md"


def _build_tree(tmp_path: Path, *, liur: bool) -> Path:
    sys.path.insert(0, str(SCRIPTS))
    from build_trime_package import build_tree

    dest = tmp_path / "tree"
    build_tree(
        dest,
        liur_dir=LIUR_DIR if liur else None,
        rime_data_dir=RIME_DATA,
    )
    return dest


def _rel_names(tree: Path) -> set[str]:
    return {str(p.relative_to(tree)) for p in tree.rglob("*") if p.is_file()}


def test_phah_only_overlay_carries_core_and_reverse_deps(tmp_path: Path) -> None:
    """--no-liur 仍是自足的拍台文 overlay: 核心檔 + 反查閉包 + @next 註冊."""
    tree = _build_tree(tmp_path, liur=False)

    names = _rel_names(tree)
    for name in [*REQUIRED_PHAH, *REQUIRED_REVERSE, INSTALL_NAME, "rime.lua", "default.custom.yaml"]:
        assert name in names, f"缺少 {name}"

    assert len(list((tree / "lua").glob("phah_taibun_*.lua"))) == 19
    assert not list((tree / "lua").glob("liu_*.lua"))

    rime_lua = (tree / "rime.lua").read_text(encoding="utf-8")
    assert 'require("phah_taibun_data")' in rime_lua
    assert "liu_w2c_sorter" not in rime_lua

    patch = yaml.safe_load((tree / "default.custom.yaml").read_text(encoding="utf-8"))["patch"]
    assert patch["schema_list/@next"] == {"schema": "phah_taibun"}
    assert patch["schema_list/@next 1"] == {"schema": "phah_taibun_telex"}
    assert patch["switcher/save_options/@before 0"] == "poj_mode"
    assert patch["switcher/save_options/@next"] == "full_romanization"


def test_zip_is_deterministic_and_sorted(tmp_path: Path) -> None:
    """同一份輸入兩次建包必須位元組一致 (PLAN 9-3J), 條目依路徑排序."""
    sys.path.insert(0, str(SCRIPTS))
    from build_trime_package import build_zip

    payloads = []
    for run in range(2):
        tree = _build_tree(tmp_path / f"src{run}", liur=False)
        out = tmp_path / f"PhahTaiBun-Trime-{run}.zip"
        build_zip(tree, out)
        payloads.append(out.read_bytes())
        with zipfile.ZipFile(out) as archive:
            names = archive.namelist()
        assert names == sorted(names)

    assert payloads[0] == payloads[1]


@pytest.mark.skipif(not LIUR_DIR.exists(), reason="需要本地 rime-liur-arch checkout")
def test_liur_closure_is_complete_and_filtered(tmp_path: Path) -> None:
    """嘸蝦米閉包比照 install_windows.ps1 Step 3.5: root + lua + opencc, 桌面檔與字體排除."""
    tree = _build_tree(tmp_path, liur=True)

    names = _rel_names(tree)
    for name in REQUIRED_LIUR:
        assert name in names, f"缺少 {name}"

    # mixed 版 (含英文詞庫) = configs/liur.schema.yaml
    expected = LIUR_DIR / "configs" / "liur.schema.yaml"
    assert (tree / "liur.schema.yaml").read_bytes() == expected.read_bytes()

    # lua 閉包: 根層攤平, lunar_calendar 保子目錄 (同 Windows 安裝器)
    liur_lua_root = {p.name for p in (LIUR_DIR / "lua").glob("*.lua")}
    tree_lua_root = {p.name for p in (tree / "lua").glob("*.lua")}
    assert liur_lua_root <= tree_lua_root
    lunar_src = {p.name for p in (LIUR_DIR / "lua" / "lunar_calendar").iterdir() if p.is_file()}
    lunar_tree = {p.name for p in (tree / "lua" / "lunar_calendar").iterdir() if p.is_file()}
    assert lunar_src == lunar_tree

    # opencc 閉包整目錄
    opencc_src = {p.name for p in (LIUR_DIR / "opencc").iterdir() if p.is_file()}
    opencc_tree = {p.name for p in (tree / "opencc").iterdir() if p.is_file()}
    assert opencc_src == opencc_tree
    assert "liu_w2c.txt" in opencc_tree

    for forbidden in FORBIDDEN_NAMES:
        assert forbidden not in names, f"不應打包 {forbidden}"
        assert not any(n.startswith(f"{forbidden}/") for n in names), f"不應打包 {forbidden}/"


@pytest.mark.skipif(not LIUR_DIR.exists(), reason="需要本地 rime-liur-arch checkout")
def test_merged_rime_lua_registers_both_suites_once(tmp_path: Path) -> None:
    """rime.lua = 拍台文註冊 + liur 全檔附加; liur 區塊只出現一次 (marker 防重複)."""
    tree = _build_tree(tmp_path, liur=True)
    rime_lua = (tree / "rime.lua").read_text(encoding="utf-8")

    assert 'require("phah_taibun_data")' in rime_lua
    assert rime_lua.count('liu_w2c_sorter = require("liu_w2c_sorter")') == 1
    assert rime_lua.count("registrations appended") == 1
    assert "liu_schema_switch_processor" in rime_lua


@pytest.mark.skipif(not LIUR_DIR.exists(), reason="需要本地 rime-liur-arch checkout")
def test_default_custom_registers_liur_easy_en_and_bopomofo(tmp_path: Path) -> None:
    """Trime 包的 default.custom.yaml 以 @next 追加五個方案, 不覆蓋 Trime 內建清單."""
    tree = _build_tree(tmp_path, liur=True)
    patch = yaml.safe_load((tree / "default.custom.yaml").read_text(encoding="utf-8"))["patch"]

    assert patch["schema_list/@next 2"] == {"schema": "liur"}
    assert patch["schema_list/@next 3"] == {"schema": "easy_en"}
    assert patch["schema_list/@next 4"] == {"schema": "bopomofo_tw"}


def test_install_doc_ships_verbatim_from_packaging_dir(tmp_path: Path) -> None:
    """zip 內 INSTALL-Trime.md 必須逐字來自 packaging/android/ (單一事實來源)."""
    tree = _build_tree(tmp_path, liur=False)

    source = REPO / "packaging" / "android" / INSTALL_NAME
    assert source.exists(), "packaging/android/INSTALL-Trime.md 不存在"
    assert (tree / INSTALL_NAME).read_bytes() == source.read_bytes()


def test_trime_theme_patch_ships_inert_with_documented_options(tmp_path: Path) -> None:
    """排版 patch 進包但預設不生效 (空 patch): 版面未經實機驗證, 不替使用者改外觀.

    檔內範例必須涵蓋 Trime v3.3.12 trime.yaml style 段的既有鍵名, 否則使用者照抄會無效.
    """
    tree = _build_tree(tmp_path, liur=False)
    patch_file = tree / "trime.custom.yaml"
    assert patch_file.exists(), "trime.custom.yaml 未進包"

    source = REPO / "packaging" / "android" / "trime.custom.yaml"
    assert patch_file.read_bytes() == source.read_bytes()

    text = patch_file.read_text(encoding="utf-8")
    patch = yaml.safe_load(text)["patch"]
    assert patch == {}, "出貨預設不可覆蓋使用者外觀"

    for key in [
        "style/comment_position",
        "style/comment_text_size",
        "style/comment_height",
        "style/candidate_view_height",
        "style/candidate_padding",
    ]:
        assert f"#   {key}:" in text, f"範例缺少 {key}"
    assert "48" in text, "top 模式的候選列高度必須給足, 否則註解被裁切"


@pytest.mark.skipif(shutil.which("rime_deployer") is None, reason="需要系統 rime_deployer")
def test_deployer_smoke_builds_all_registered_schemas(tmp_path: Path) -> None:
    """真 librime 引擎部署整個 overlay: 拍台文與注音必過; 有 liur checkout 時連嘸蝦米也驗."""
    with_liur = LIUR_DIR.exists()
    tree = _build_tree(tmp_path, liur=with_liur)
    staging = tmp_path / "build"

    # smoke 部署的就是最終含授權載荷的 overlay
    assert (tree / "THIRD-PARTY-NOTICES.txt").exists()
    assert (tree / "licenses" / "LGPL-3.0.txt").exists()

    result = subprocess.run(
        ["rime_deployer", "--build", str(tree), str(RIME_DATA), str(staging)],
        capture_output=True,
        text=True,
        timeout=1800,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    compiled_schemas = [
        "phah_taibun.schema.yaml",
        "phah_taibun_telex.schema.yaml",
        "bopomofo_tw.schema.yaml",
    ]
    if with_liur:
        compiled_schemas += ["liur.schema.yaml", "easy_en.schema.yaml"]
    for compiled in compiled_schemas:
        assert (staging / compiled).exists(), f"部署產物缺少 {compiled}"
    assert (staging / "default.yaml").exists()


def test_cli_default_bundle_is_the_liur_free_variant(tmp_path: Path) -> None:
    """預設產物 = 不含嘸蝦米的輕量包; 要嘸蝦米必須明確 --with-liur (使用者自選)."""
    output = tmp_path / "release.zip"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "build_trime_package.py"), "--output", str(output)],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()

    assert "phah_taibun.schema.yaml" in names
    assert "bopomofo_tw.schema.yaml" in names
    assert "THIRD-PARTY-NOTICES.txt" in names
    assert "licenses/LGPL-3.0.txt" in names
    assert "licenses/GPL-3.0.txt" in names
    assert "LICENSE-PhahTaiBun.txt" in names
    assert "trime.custom.yaml" in names
    assert "liur.schema.yaml" not in names
    assert "LIUR-PROVENANCE.txt" not in names
    assert not any(name.startswith("lua/liu_") for name in names)
    assert not any(name.startswith("opencc/") for name in names)


def test_cli_with_liur_naming_does_not_clobber_the_light_bundle() -> None:
    """--with-liur 未指定 --output 時輸出加 -liur 後綴 (release 靠此分流), 指定則尊重使用者."""
    sys.path.insert(0, str(SCRIPTS))
    import build_trime_package as btp

    default = Path("/repo/dist/PhahTaiBun-Trime.zip")
    assert btp._resolve_output(default, with_liur=True, is_default=True) == Path(
        "/repo/dist/PhahTaiBun-Trime-liur.zip"
    )
    assert btp._resolve_output(default, with_liur=False, is_default=True) == default
    explicit = Path("/tmp/my.zip")
    assert btp._resolve_output(explicit, with_liur=True, is_default=False) == explicit

@pytest.mark.skipif(not LIUR_DIR.exists(), reason="需要本地 rime-liur-arch checkout")
def test_liur_bundle_records_provenance(tmp_path: Path) -> None:
    """--with-liur 的包必須附 provenance: remote, commit, 上游譜系與授權宣告; 不含機器路徑."""
    tree = _build_tree(tmp_path, liur=True)
    notice = (tree / "LIUR-PROVENANCE.txt").read_text(encoding="utf-8")

    assert "source remote: https://github.com/soanseng/rime-liur-arch" in notice
    assert "commit:" in notice
    assert "upstream: ryanwuson/rime-liur" in notice
    assert "license:" in notice
    assert "基於開源授權發佈" in notice
    assert "source path:" not in notice


def test_third_party_notices_and_license_texts_are_bundled(tmp_path: Path) -> None:
    sys.path.insert(0, str(SCRIPTS))
    from build_trime_package import build_zip

    tree = _build_tree(tmp_path, liur=False)
    archive_path = build_zip(tree, tmp_path / "release.zip")

    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        for required in [
            "THIRD-PARTY-NOTICES.txt",
            "LICENSE-PhahTaiBun.txt",
            "licenses/LGPL-3.0.txt",
            "licenses/GPL-3.0.txt",
        ]:
            assert required in names, f"缺少 {required}"
        notice = archive.read("THIRD-PARTY-NOTICES.txt").decode("utf-8")
        lgpl = archive.read("licenses/LGPL-3.0.txt").decode("utf-8")
        gpl = archive.read("licenses/GPL-3.0.txt").decode("utf-8")
        project_license = archive.read("LICENSE-PhahTaiBun.txt").decode("utf-8")

        # notice 標示的雜湊必須等於封裝內實際位元組, 否則標示形同虛設
        for name in REQUIRED_REVERSE:
            digest = hashlib.sha256(archive.read(name)).hexdigest()
            assert digest in notice, f"{name} 的 sha256 未標示或與封裝內容不符"

    assert "LGPL-3.0" in notice
    assert "https://github.com/rime/rime-bopomofo" in notice
    assert "https://github.com/rime/rime-terra-pinyin" in notice
    assert "GONG Chen <chen.sst@gmail.com>" in notice
    assert "Kunki Chiu <cokunhui@gmail.com>" in notice
    assert "未做任何修改" in notice

    assert "GNU LESSER GENERAL PUBLIC LICENSE" in lgpl
    assert "Version 3, 29 June 2007" in lgpl
    assert "GNU GENERAL PUBLIC LICENSE" in gpl
    assert "MIT License" in project_license
