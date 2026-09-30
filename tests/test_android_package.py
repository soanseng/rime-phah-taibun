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
    "phah_taibun.wordlist",
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


@pytest.mark.skipif(not RIME_DATA.exists(), reason="需要系統 rime-data (terra_pinyin/bopomofo 反查依賴)")
def test_phah_only_overlay_carries_core_and_reverse_deps(tmp_path: Path) -> None:
    """--no-liur 仍是自足的拍台文 overlay: 核心檔 + 反查閉包 + @next 註冊."""
    tree = _build_tree(tmp_path, liur=False)

    names = _rel_names(tree)
    for name in [*REQUIRED_PHAH, *REQUIRED_REVERSE, INSTALL_NAME, "rime.lua", "default.custom.yaml"]:
        assert name in names, f"缺少 {name}"

    assert len(list((tree / "lua").glob("phah_taibun_*.lua"))) == 21
    assert not list((tree / "lua").glob("liu_*.lua"))

    rime_lua = (tree / "rime.lua").read_text(encoding="utf-8")
    assert 'require("phah_taibun_data")' in rime_lua
    assert "liu_w2c_sorter" not in rime_lua

    patch = yaml.safe_load((tree / "default.custom.yaml").read_text(encoding="utf-8"))["patch"]
    assert patch["schema_list/@next"] == {"schema": "phah_taibun"}
    assert patch["schema_list/@next 1"] == {"schema": "phah_taibun_telex"}
    assert patch["switcher/save_options/@before 0"] == "poj_mode"
    assert patch["switcher/save_options/@next"] == "full_romanization"


@pytest.mark.skipif(not RIME_DATA.exists(), reason="需要系統 rime-data (terra_pinyin/bopomofo 反查依賴)")
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

    # opencc 閉包: liur 整目錄 + 拍台文自帶 emoji 資產
    opencc_src = {p.name for p in (LIUR_DIR / "opencc").iterdir() if p.is_file()}
    opencc_tree = {p.name for p in (tree / "opencc").iterdir() if p.is_file()}
    assert opencc_src <= opencc_tree
    assert {"emoji.json", "emoji_word.txt", "emoji_category.txt"} <= opencc_tree
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


@pytest.mark.skipif(not RIME_DATA.exists(), reason="需要系統 rime-data (terra_pinyin/bopomofo 反查依賴)")
def test_install_doc_ships_verbatim_from_packaging_dir(tmp_path: Path) -> None:
    """zip 內 INSTALL-Trime.md 必須逐字來自 packaging/android/ (單一事實來源)."""
    tree = _build_tree(tmp_path, liur=False)

    source = REPO / "packaging" / "android" / INSTALL_NAME
    assert source.exists(), "packaging/android/INSTALL-Trime.md 不存在"
    assert (tree / INSTALL_NAME).read_bytes() == source.read_bytes()


@pytest.mark.skipif(not RIME_DATA.exists(), reason="需要系統 rime-data (terra_pinyin/bopomofo 反查依賴)")
def test_trime_patch_ships_verbatim_and_enables_comment_annotation(tmp_path: Path) -> None:
    """trime.custom.yaml 逐字進包, 且候選註解 (拼音) 預設生效 (A-a).

    桌面版候選一律「漢字+拼音註解」; Trime 內建註解 10sp 太小, 0.9.0 起
    預設放大, 不再是空 patch — 註解與功能列都是拍台文手機輸入的必要操作.
    """
    tree = _build_tree(tmp_path, liur=False)
    patch_file = tree / "trime.custom.yaml"
    assert patch_file.exists(), "trime.custom.yaml 未進包"

    source = REPO / "packaging" / "android" / "trime.custom.yaml"
    assert patch_file.read_bytes() == source.read_bytes()

    patch = yaml.safe_load(patch_file.read_text(encoding="utf-8"))["patch"]
    assert patch["style/comment_position"] == "right"
    assert patch["style/comment_text_size"] >= 12, "註解至少 12sp 才看得清拼音"
    assert patch["style/candidate_view_height"] >= 30, "列高須容納候選字+註解"

    # top 模式範例保留在註解, 供窄螢幕使用者改版; 鍵名須存在於 Trime v3.3.12
    text = patch_file.read_text(encoding="utf-8")
    for key in [
        "style/comment_position",
        "style/comment_height",
        "style/candidate_view_height",
        "style/candidate_padding",
    ]:
        assert f"#   {key}:" in text, f"top 模式範例缺少 {key}"
    assert "48" in text, "top 模式的候選列高度必須給足, 否則註解被裁切"


@pytest.mark.skipif(not RIME_DATA.exists(), reason="需要系統 rime-data (terra_pinyin/bopomofo 反查依賴)")
def test_trime_patch_defines_taigi_function_keys(tmp_path: Path) -> None:
    """preset_keys 定義 Tab 選字、羅馬字標記與 TL/POJ、漢羅/全羅切換鍵 (A-b/c/e).

    toggle 的選項名必須是 schema switches 的實際名稱, 且已列入
    default.custom.yaml 的 save_options — Trime 按鍵切換的模式才會跨 session 記憶.
    """
    tree = _build_tree(tmp_path, liur=False)
    patch = yaml.safe_load((tree / "trime.custom.yaml").read_text(encoding="utf-8"))["patch"]
    pk = {k.split("/", 1)[1]: v for k, v in patch.items() if k.startswith("preset_keys/")}
    assert pk["Taigi_Tab"]["send"] == "Tab", "桌面 Tab 逐詞選字在 Trime 靠這顆鍵"
    assert pk["Taigi_Roman"]["send"] == "backslash", "手動漢羅的 \\ 標記鍵"
    # send: SWITCH_CHARSET 是必要條件: Trime 的 CommonKeyboardActionListener
    # 只在 KEYCODE_SWITCH_CHARSET 路徑呼叫 handleSwitchCharset (set_option);
    # 對照內建 Mode_switch preset 的寫法, 少了它 toggle 不會觸發.
    assert pk["Taigi_Poj"]["send"] == "SWITCH_CHARSET"
    assert pk["Taigi_Hanlo"]["send"] == "SWITCH_CHARSET"
    assert pk["Taigi_Poj"]["toggle"] == "poj_mode"
    assert pk["Taigi_Poj"]["states"] == ["TL", "POJ"]
    assert pk["Taigi_Hanlo"]["toggle"] == "full_romanization"
    assert pk["Taigi_Hanlo"]["states"] == ["漢羅", "全羅"]

    switches = yaml.safe_load(
        (REPO / "schema" / "phah_taibun.schema.yaml").read_text(encoding="utf-8")
    )["switches"]
    names = {s["name"] for s in switches}
    assert {"poj_mode", "full_romanization"} <= names, "toggle 名稱必須對應 schema switch"
    dc = yaml.safe_load((REPO / "schema" / "default.custom.yaml").read_text(encoding="utf-8"))["patch"]
    saved = {v for k, v in dc.items() if k.startswith("switcher/save_options")}
    assert {"poj_mode", "full_romanization"} <= saved, "切換鍵的模式必須會被 save_options 保存"


@pytest.mark.skipif(not RIME_DATA.exists(), reason="需要系統 rime-data (terra_pinyin/bopomofo 反查依賴)")
def test_trime_patch_defines_schema_keyboards_and_panel(tmp_path: Path) -> None:
    """拍台文鍵盤=上游 26 鍵版面+中文鍵長按面板; 其他方案鍵盤零改動 (2026-09-30 定案).

    - 無矮功能列: patch 不得用清單運算 (@next) 修改上游 qwerty/default 鍵盤
    - phah_taibun / phah_taibun_telex 專屬鍵盤 (Trime 依方案 id 配對同名鍵盤),
      版面=上游 26 鍵 (37 keys), 僅中文鍵長按從 Menu 改 Taigi_Panel
    - 面板 taigi_panel 一列六鍵, 寬度和恰為 100 才會自成一列
    - config_version 必須 bump (≠上游 "3.0"), 升級安裝才會重新部署主題
    """
    tree = _build_tree(tmp_path, liur=False)
    patch = yaml.safe_load((tree / "trime.custom.yaml").read_text(encoding="utf-8"))["patch"]

    assert not [k for k in patch if k.startswith(("preset_keyboards/qwerty", "preset_keyboards/default"))], (
        "上游 qwerty/default 鍵盤必須零改動 (其他方案共用)"
    )
    assert patch["config_version"] != "3.0", "主題 config_version 須 bump 才會觸發重部署"

    for kb in ("phah_taibun", "phah_taibun_telex"):
        keys = patch[f"preset_keyboards/{kb}"]["keys"]
        assert len(keys) == 37, f"{kb} 應為上游 26 鍵版面 (37 keys)"
        mode = [k for k in keys if k.get("click") == "Mode_switch"]
        assert mode and mode[0]["long_click"] == "Taigi_Panel", f"{kb} 中文鍵長按應開拍台文面板"

    panel = patch["preset_keyboards/taigi_panel"]["keys"]
    assert [k["click"] for k in panel] == [
        "Taigi_Tab",
        "Taigi_Roman",
        "Taigi_Poj",
        "Taigi_Hanlo",
        "Taigi_Menu",
        "Taigi_Back",
    ], "面板=選字/羅/TL-POJ/漢全羅/方案選單/返回"
    assert sum(k["width"] for k in panel) == 100, "面板寬度和須為 100 (自成一列)"
    assert patch["preset_keys/BackSpace/label"] == "←", "退格鍵面=倒退箭頭"
    fixbar = patch["liquid_keyboard/fixed_key_bar/keys"]
    assert fixbar[-1] == "Settings", "「…」面板固定列加設定入口"
    assert fixbar[:6] == [
        "liquid_keyboard_exit",
        "space1",
        "BackSpace",
        "Return2",
        "clipboard_window",
        "liquid_keyboard_switch",
    ], "上游固定列鍵全數保留"


@pytest.mark.skipif(not RIME_DATA.exists(), reason="需要系統 rime-data (terra_pinyin/bopomofo 反查依賴)")
@pytest.mark.skipif(not LIUR_DIR.exists(), reason="需要本地 rime-liur-arch checkout")
def test_apk_assets_tree_is_full_f2_closure_without_overlay_extras(tmp_path: Path) -> None:
    """--apk-assets 產 Trime 客製 APK 的 assets/shared 內容樹 (F2: 台語+注音+嘸蝦米全包).

    主題=基座+patch 的確定性烘焙成品 (runtime 部署競態不可靠, 見
    _bake_trime_theme); trime.custom.yaml 本身不進 assets; 方案註冊由
    fork 的 DataManager (SCHEMA_LIST_CUSTOM_PATCH) 提供; 授權標示
    (THIRD-PARTY-NOTICES / licenses / LIUR-PROVENANCE) 仍須隨包.
    """
    sys.path.insert(0, str(SCRIPTS))
    import build_trime_package as btp

    dest = btp.build_apk_assets(tmp_path / "shared", liur_dir=LIUR_DIR, rime_data_dir=RIME_DATA)
    names = _rel_names(dest)

    for required in REQUIRED_PHAH + REQUIRED_REVERSE + REQUIRED_LIUR:
        assert required in names, f"APK 閉包缺 {required}"
    assert "lua/phah_taibun_filter.lua" in names
    assert "lua/liu_w2c_sorter.lua" in names, "F2 全包必須含嘸蝦米 lua"
    rime_lua = (dest / "rime.lua").read_text(encoding="utf-8")
    assert rime_lua.count("rime-liur) registrations appended") == 1, "liur 註冊只附加一次"

    for overlay_only in ("INSTALL-Trime.md", "trime.custom.yaml", "default.custom.yaml"):
        assert overlay_only not in names, f"{overlay_only} 不進 APK assets"
    theme = yaml.safe_load((dest / "trime.yaml").read_text(encoding="utf-8"))
    assert theme["config_version"] != "3.0", "烘焙主題需帶 bump 過的 config_version"
    assert theme["preset_keyboards"]["phah_taibun"]["keys"], "烘焙主題需含拍台文鍵盤"
    assert theme["preset_keys"]["BackSpace"]["label"] == "←"
    assert "Settings" in theme["liquid_keyboard"]["fixed_key_bar"]["keys"], "…面板含設定入口"
    assert theme["preset_keys"]["Menu"]["send"] == "MENU", "上游 Menu preset 不動"
    assert (dest / "build" / "trime.yaml").read_text(encoding="utf-8") == (
        dest / "trime.yaml"
    ).read_text(encoding="utf-8"), "prebuilt fallback (shared/build) 須與主題同步"
    assert "THIRD-PARTY-NOTICES.txt" in names
    assert "licenses/LGPL-3.0.txt" in names
    assert "LIUR-PROVENANCE.txt" in names


@pytest.mark.skipif(not RIME_DATA.exists(), reason="需要系統 rime-data (terra_pinyin/bopomofo 反查依賴)")
@pytest.mark.skipif(not LIUR_DIR.exists(), reason="需要本地 rime-liur-arch checkout")
def test_cli_apk_assets_mode_exits_zero(tmp_path: Path) -> None:
    """--apk-assets 走 CLI 也通: 產出目錄存在且無 zip 副產物."""
    sys.path.insert(0, str(SCRIPTS))
    import build_trime_package as btp

    dest = tmp_path / "assets-shared"
    rc = btp.main(
        [
            "--with-liur",
            "--apk-assets",
            str(dest),
            "--liur-dir",
            str(LIUR_DIR),
            "--rime-data-dir",
            str(RIME_DATA),
        ]
    )
    assert rc == 0
    assert (dest / "phah_taibun.schema.yaml").is_file()
    assert (dest / "rime.lua").is_file()


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


@pytest.mark.skipif(not RIME_DATA.exists(), reason="需要系統 rime-data (terra_pinyin/bopomofo 反查依賴)")
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
    # opencc/ 現在是拍台文自帶的 Emoji 資產 (rime-emoji, LGPL-3.0),
    # 預設包就要有; 嘸蝦米的 liur 變體檔案仍不在.
    assert "opencc/emoji.json" in names
    assert "opencc/emoji_word.txt" in names
    assert "opencc/emoji_category.txt" in names


def test_cli_with_liur_naming_does_not_clobber_the_light_bundle() -> None:
    """--with-liur 未指定 --output 時輸出加 -liur 後綴 (release 靠此分流), 指定則尊重使用者."""
    sys.path.insert(0, str(SCRIPTS))
    import build_trime_package as btp

    default = Path("/repo/dist/PhahTaiBun-Trime.zip")
    assert btp._resolve_output(default, with_liur=True, is_default=True) == Path("/repo/dist/PhahTaiBun-Trime-liur.zip")
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


@pytest.mark.skipif(not RIME_DATA.exists(), reason="需要系統 rime-data (terra_pinyin/bopomofo 反查依賴)")
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


def test_schemas_use_express_editor_for_direct_commit() -> None:
    """A-d 釘住: 選字(含點擊候選)涵蓋全部輸入必須直接上屏.

    librime ConcreteEngine::OnSelect (engine.cc) 只在 _auto_commit 開啟時 commit,
    而 _auto_commit 由 Editor 建構子設定: fluency_editor=false(點候選只進組字,
    需再按空白)、express_editor=true。上游 luna_pinyin(逐詞)= express_editor。
    真機重現與修復見 rime-trime-taigi fix(schema) commit(Solana Seeker 驗證)。
    """
    for name in ("phah_taibun.schema.yaml", "phah_taibun_telex.schema.yaml"):
        processors = yaml.safe_load((REPO / "schema" / name).read_text(encoding="utf-8"))["engine"]["processors"]
        assert "express_editor" in processors, f"{name} 缺 express_editor — 點候選不會直接上屏(A-d)"
        assert "fluency_editor" not in processors, f"{name} 殘留 fluency_editor — 點候選只進組字(A-d)"


def test_fluency_variant_keeps_continuous_composition() -> None:
    """桌面連打保留: phah_taibun_fluency 變體必須用 fluency_editor.

    整句連打逐詞選字(選字確認進組字累積、Enter/空白整句上屏)= fluency_editor
    語意; 主案兩個 schema 用 express_editor(A-d 直接上屏), 連打工作流由本
    變體延續(上游 luna_pinyin vs luna_pinyin_fluency 同款分工)。
    """
    processors = yaml.safe_load((REPO / "schema" / "phah_taibun_fluency.schema.yaml").read_text(encoding="utf-8"))[
        "engine"
    ]["processors"]
    assert "fluency_editor" in processors, "phah_taibun_fluency 缺 fluency_editor — 連打選字語意消失"
    assert "express_editor" not in processors, "phah_taibun_fluency 不應是 express_editor — 那就與主案重複"
    fluency = yaml.safe_load((REPO / "schema" / "phah_taibun_fluency.schema.yaml").read_text(encoding="utf-8"))
    assert fluency["__include"].startswith("phah_taibun.schema.yaml"), "變體必須繼承主案(其餘設定不重複)"
