import shutil
import subprocess
from pathlib import Path

import pytest
import yaml


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def read_prefix(path: str, lines: int = 10) -> str:
    with Path(path).open(encoding="utf-8") as handle:
        return "".join(next(handle, "") for _ in range(lines))


def test_windows_inno_setup_runs_existing_powershell_installer():
    iss = read("packaging/windows/phah-taibun.iss")
    installer = read("install_windows.ps1")

    assert "Phah Tai-bun" in iss
    assert "install_windows.ps1" in iss
    assert "powershell.exe" in iss
    assert "-ExecutionPolicy Bypass" in iss
    assert "PHAH_TAIBUN_PROJECT_ROOT" in iss
    assert "PrivilegesRequired=lowest" in iss
    assert "DefaultDirName={localappdata}\\Phah Tai-bun" in iss
    assert "Exec(" in iss
    assert "ewWaitUntilTerminated" in iss
    assert "ResultCode <> 0" in iss
    assert "RaiseException" in iss
    assert "postinstall" not in iss
    assert "$env:PHAH_TAIBUN_PROJECT_ROOT" in installer
    assert "$ProjectRoot" in installer
    assert "Copy-OrDownload" in installer
    assert 'Copy-OrDownload -SourcePath "schema/default.custom.yaml" -DestinationPath $defaultCustom' in installer


def test_windows_installer_appends_schema_without_utf16_rewrite():
    """Existing Rime schema_list must stay; PS 5.1 Add-Content would UTF-16-corrupt it."""
    installer = read("install_windows.ps1")
    assert "UTF8Encoding $false" in installer
    assert "Add-Content" not in installer
    assert "Set-Content" not in installer
    assert "schema_list/@next" in installer
    assert "不會因此取代" in installer or "保留既有方案" in installer
    assert '$needRegister = $true' in installer
    assert 'schema_list/@next:`n        schema: phah_taibun' in installer
    assert "default.custom.yaml.bak" in installer


def test_windows_packaged_installer_hides_powershell_and_survives_deploy_fail():
    """GUI setup must not flash a console; deploy fail is manual 重新部署 like rime-liur."""
    iss = read("packaging/windows/phah-taibun.iss")
    installer = read("install_windows.ps1")
    homepage = read("docs/index.html")

    assert "SW_HIDE" in iss
    assert "SW_SHOW" not in iss
    assert "-WindowStyle Hidden" in iss
    assert "DOWNLOADED_PAYLOAD" in installer
    assert 'if (-not $DOWNLOADED_PAYLOAD)' in installer
    assert "右鍵工作列小狼毫圖示" in installer
    windows_panel = homepage.split('id="panel-windows"', 1)[1].split('id="panel-macos"', 1)[0]
    assert "install_windows.ps1" in windows_panel
    assert "irm " in windows_panel
    assert "| iex" in windows_panel


def test_windows_installer_is_bom_free_and_iex_safe():
    """A BOM breaks `irm ... | iex`: iex glues the BOM onto the first token, so a
    top-level param()/comment fails to parse (reproduced verbatim on a Windows report:
    "At line:6 char:28 ... $ProjectRoot = \"\","). Keep the script BOM-free and free of
    a top-level param(); parameters travel via env vars or $args instead."""
    raw = Path("install_windows.ps1").read_bytes()
    text = raw.decode("utf-8")

    assert not raw.startswith(b"\xef\xbb\xbf"), "a BOM would break `irm ... | iex`"
    assert not any(line.startswith("param(") for line in text.splitlines())
    assert "$env:PHAH_TAIBUN_PROJECT_ROOT" in text
    assert "$env:PHAH_TAIBUN_SCHEMAS" in text
    # packaged installer must read the BOM-less file as UTF-8 and iex it, not -File it
    iss = read("packaging/windows/phah-taibun.iss")
    assert "iex ([System.IO.File]::ReadAllText(" in iss
    assert "PHAH_TAIBUN_PROJECT_ROOT" in iss


def test_windows_installer_parses_as_iex_payload():
    """Drive the real `irm | iex` parse path: ReadAllText(UTF8) then create a scriptblock."""
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        pytest.skip("pwsh not available to verify the iex parse path")

    code = (
        "$src = [System.IO.File]::ReadAllText('install_windows.ps1', [System.Text.Encoding]::UTF8);"
        "try { [void][scriptblock]::Create($src); 'PARSE-OK' }"
        "catch { 'PARSE-FAIL: ' + $_.Exception.Message }"
    )
    out = subprocess.run(
        [pwsh, "-NoProfile", "-Command", code], capture_output=True, text=True, cwd="."
    )
    assert "PARSE-OK" in out.stdout, out.stdout + out.stderr

def test_release_payload_excludes_unused_standalone_reverse_dictionary():
    assert not Path("schema/phah_taibun_reverse.dict.yaml").exists()
    assert "phah_taibun_reverse.dict.yaml" not in read("scripts/build_all.py")
    assert "phah_taibun_reverse.dict.yaml" not in read("scripts/install_linux.sh")
    assert "phah_taibun_reverse.dict.yaml" not in read("scripts/install_macos.sh")
    assert "phah_taibun_reverse.dict.yaml" not in read("install_windows.ps1")


def test_macos_pkg_builder_uses_existing_macos_installer():
    build = read("packaging/macos/build-pkg.sh")
    postinstall = read("packaging/macos/scripts/postinstall")

    assert "pkgbuild" in build
    assert "productbuild" in build
    assert "install_macos.sh" in postinstall
    assert "--project-root" in postinstall
    assert "/dev/console" in postinstall
    assert "sudo -u" in postinstall
    installer = read("scripts/install_macos.sh")
    assert "--project-root" in installer
    assert "PHAH_TAIBUN_ARCHIVE_URL" in installer
    assert "mktemp -d" in installer
    assert "tar -xf" in installer
    assert "trap cleanup EXIT" in installer


def test_installers_fail_loudly_when_rime_deployment_fails():
    linux = read("scripts/install_linux.sh")
    macos = read("scripts/install_macos.sh")
    windows = read("install_windows.ps1")

    assert 'rime_deployer --build "$RIME_DIR" 2>/dev/null || true' not in linux
    assert 'fcitx5-remote -r 2>/dev/null || true' not in linux
    assert 'ibus restart 2>/dev/null || true' not in linux
    assert "部署失敗" in linux
    assert "if ! open -a Squirrel" in macos
    assert "部署失敗" in macos
    assert "WeaselDeployer.exe" in windows
    assert "Start-Process" in windows
    assert "ExitCode" in windows
    assert "部署失敗" in windows


def test_remote_installer_assets_are_versioned_and_sha256_verified():
    linux = read("scripts/install_linux.sh")
    macos = read("scripts/install_macos.sh")
    windows = read("install_windows.ps1")
    workflow = read(".github/workflows/release.yml")

    assert "/ButTaiwan/iansui/main/" not in linux
    assert "/ButTaiwan/iansui/main/" not in macos
    assert "/ButTaiwan/iansui/main/" not in windows
    assert "7f1aa62e9dcbf40d0ce41a5d3f1e5ea602e66c295778ac6fefb6b84d8ed08bd5" in linux
    assert "7f1aa62e9dcbf40d0ce41a5d3f1e5ea602e66c295778ac6fefb6b84d8ed08bd5" in macos
    assert "7f1aa62e9dcbf40d0ce41a5d3f1e5ea602e66c295778ac6fefb6b84d8ed08bd5" in windows
    assert "sha256sum" in linux
    assert "shasum -a 256" in macos
    assert "Get-FileHash" in windows
    assert "SOURCE_ARCHIVE_SHA256_URL" in macos
    assert "PhahTaiBun-source.zip.sha256" in windows
    assert "PhahTaiBun-source.zip.sha256" in workflow
    resources = read("scripts/download_resources.sh")
    assert "git clone --depth 1" not in resources
    assert 'git -C "$dest" fetch -q --depth 1 origin "$revision"' in resources
    assert ".source-revision" in resources
    assert "download_verified" in resources


def test_installers_upgrade_existing_default_custom_with_save_options():
    """Re-running an installer on an old default.custom.yaml must add save_options.

    Existing users' files already contain phah_taibun, so the schema
    registration step skips them; the installer must still add the
    poj_mode/full_romanization save_options lines or the romanization choice
    keeps resetting on every new session.
    """
    for installer in (
        read("scripts/install_linux.sh"),
        read("scripts/install_macos.sh"),
        read("install_windows.ps1"),
    ):
        assert "poj_mode" in installer
        assert "full_romanization" in installer
        assert "switcher/save_options" in installer


def test_installers_ship_and_register_the_telex_schema():
    """拍台文(Telex) must be shipped and registered like the main schema.

    Existing users' default.custom.yaml already contains phah_taibun, so the
    main registration step skips; each installer needs its own append step for
    phah_taibun_telex (Step 2.55) or upgrades never expose the new schema.
    """
    linux = read("scripts/install_linux.sh")
    macos = read("scripts/install_macos.sh")
    windows = read("install_windows.ps1")

    assert '"phah_taibun_telex.schema.yaml"' in linux
    assert '"phah_taibun_telex.schema.yaml"' in macos
    # Windows ships every schema/*.yaml via glob; assert registration instead.
    assert "已將 phah_taibun_telex 追加到 default.custom.yaml" in linux
    assert "已將 phah_taibun_telex 追加到 default.custom.yaml" in macos
    assert "已將 phah_taibun_telex 追加到 default.custom.yaml" in windows


def test_release_version_is_consistent_across_runtime_and_packaging_metadata():
    version = "0.7.0"

    assert f'version = "{version}"' in read("pyproject.toml")
    assert f'version: "{version}"' in read_prefix("schema/phah_taibun.schema.yaml")
    assert f'version: "{version}"' in read_prefix("schema/phah_taibun.dict.yaml")
    assert f'version: "{version}"' in read("scripts/convert_chhoetaigi.py")
    assert f'RELEASE_VERSION="{version}"' in read("scripts/install_macos.sh")
    assert f'$RELEASE_VERSION = "{version}"' in read("install_windows.ps1")
    assert f'VERSION="${{PHAH_TAIBUN_VERSION:-{version}}}"' in read(
        "packaging/macos/build-pkg.sh"
    )
    assert f'#define MyAppVersion "{version}"' in read(
        "packaging/windows/phah-taibun.iss"
    )



def test_release_packages_wait_for_complete_verification_gate():
    workflow = yaml.safe_load(read(".github/workflows/release.yml"))
    jobs = workflow["jobs"]
    verify_commands = "\n".join(
        step.get("run", "") for step in jobs["verify"]["steps"]
    )

    assert "uv run pytest" in verify_commands
    assert "RIME_SMOKE_REQUIRED=1" in verify_commands
    assert "uv run ruff check" in verify_commands
    assert "luac5.4 -p" in verify_commands
    assert "bash -n" in verify_commands
    assert "rime-prelude" in verify_commands
    for package_job in ("package-source", "package-windows"):
        assert jobs[package_job]["needs"] == "verify"
    assert "package-macos" not in jobs


def test_packaging_docs_warn_about_rime_engine_dependency():
    windows_doc = read("packaging/windows/README.md")
    mac_doc = read("packaging/macos/README.md")
    user_doc = read("docs/packaged-installers.md")

    assert "Weasel" in windows_doc
    assert "Squirrel" in mac_doc
    assert "不會覆蓋" in windows_doc
    assert "不會覆蓋" in mac_doc
    assert "PhahTaiBunSetup.exe" in user_doc


def test_release_workflow_attaches_packaged_installers():
    workflow = read(".github/workflows/release.yml")

    assert "package-macos" not in workflow
    assert "package-windows" in workflow
    assert "packaging/macos/build-pkg.sh" not in workflow
    assert "Inno Setup 6\\ISCC.exe" in workflow
    assert "PhahTaiBun.pkg" not in workflow
    assert "PhahTaiBunSetup.exe" in workflow


def test_macos_public_install_is_cli_not_pkg():
    """macOS follows rime-liur/Linux: curl or copy, no unverifiable .pkg."""
    homepage = read("docs/index.html")
    readme = read("README.md")
    guide = read("docs/user-guide.md")
    quickstart = read("docs/quickstart-card.md")
    macos_panel = homepage.split('id="panel-macos"', 1)[1].split('id="panel-linux"', 1)[0]

    assert "install_macos.sh" in macos_panel
    assert "curl -fsSL" in macos_panel
    assert "PhahTaiBun.pkg" not in macos_panel
    assert "scripts/install_macos.sh" in readme
    assert "scripts/install_macos.sh" in guide
    assert "scripts/install_macos.sh" in quickstart
    assert "PhahTaiBun.pkg" not in readme
    assert "PhahTaiBun.pkg" not in guide
    assert "PhahTaiBun.pkg" not in quickstart
    faq = homepage.split("這是手機輸入法嗎", 1)[1].split("</details>", 1)[0]
    assert "官方安裝包是電腦版" not in faq
    assert "指令" in faq

def test_public_docs_explain_supported_update_paths_and_preservation():
    readme = read("README.md")
    guide = read("docs/user-guide.md")
    quickstart = read("docs/quickstart-card.md")
    packaged = read("docs/packaged-installers.md")
    homepage = read("docs/index.html")

    for document in (readme, guide, quickstart, packaged, homepage):
        assert "更新拍台文" in document
    assert "git pull --ff-only" in readme
    assert "git pull --ff-only" in guide
    assert "PhahTaiBunSetup.exe" in packaged
    assert "scripts/install_macos.sh" in packaged
    assert "自訂詞庫" in guide
    assert "重新部署" in guide


def test_android_community_install_is_documented_without_apk():
    """Android uses existing Rime frontends; no schema change, no official APK."""
    android = read("docs/android.md")
    homepage = read("docs/index.html")
    sidebar = read("docs/_sidebar.md")
    guide = read("docs/user-guide.md")
    readme = read("README.md")

    assert "Trime" in android
    assert "fcitx5-android" in android
    assert "librime-lua" in android
    assert "phah_taibun.schema.yaml" in android
    assert "沒有官方 APK" in android or "沒有 APK" in android
    assert "android.md" in sidebar
    assert 'data-tab="android"' in homepage
    assert "android.md" in homepage
    assert "android.md" in guide
    assert "docs/android.md" in readme
    assert "panel-android" in homepage

    workflow = read(".github/workflows/release.yml")
    assert "docs/android.md" in workflow


def test_windows_installer_offers_boshiamy_as_optional_schema_choice():
    """irm|iex must let the user pick 拍台文 / 嘸蝦米 / both, from the public rime-liur-arch fork."""
    installer = read("install_windows.ps1")
    iss = read("packaging/windows/phah-taibun.iss")

    assert "soanseng/rime-liur-arch" in installer
    assert "嘸蝦米" in installer
    assert "$env:PHAH_TAIBUN_SCHEMAS" in installer
    assert "-Schemas" in installer
    assert "configs\\liur.schema.yaml" in installer
    assert "liur.chinese-only.schema.yaml" in installer
    assert "easy_en" in installer


def test_windows_installer_merges_liur_rime_lua_and_preserves_custom_files():
    """liur rime.lua defines full functions; append whole file by marker, never clobber phah requires."""
    installer = read("install_windows.ps1")

    assert "liu_w2c_sorter" in installer
    assert "openxiami_CustomWord.dict.yaml" in installer
    # rime.lua must not be in the bulk root-file download list, or it overwrites
    # the phah registrations before the merge can detect them.
    assert '$path -notmatch "/" -and $path -ne "rime.lua"' in installer


def test_windows_installer_backs_up_and_asks_which_existing_schemas_to_keep():
    """Installer must back up default.custom.yaml (timestamped) and ask what to keep."""
    installer = read("install_windows.ps1")

    assert "default.custom.yaml.backup-" in installer
    assert "要保留" in installer


def test_windows_installer_keeps_bopomofo_by_default():
    """注音 must survive the install; offer to add bopomofo when missing."""
    installer = read("install_windows.ps1")

    assert "bopomofo" in installer
    assert "注音" in installer


def test_windows_installer_never_prunes_the_schemas_it_installs():
    """A 'keep only these' answer must not unregister what this run is installing."""
    installer = read("install_windows.ps1")

    assert "$protectedIds" in installer
    assert '$protectedIds += @("phah_taibun", "phah_taibun_telex")' in installer
    assert '$protectedIds += "liur"' in installer


def test_windows_installer_never_slices_a_powershell_descending_range():
    """$lines[($lastIdx+1)..($count-1)] yields 4,3 when the schema list ends the file, duplicating the tail."""
    installer = read("install_windows.ps1")

    assert "function Get-RimeTail" in installer
    assert "[($lastIdx+1)..($lines.Count-1)]" not in installer
    assert installer.count("(Get-RimeTail -Lines $lines -AfterIndex $lastIdx)") >= 3


def test_windows_installer_normalizes_default_custom_with_comments():
    """After install, default.custom.yaml must be clean, commented, and normalized before deploy."""
    installer = read("install_windows.ps1")

    assert "function Convert-RimeDefaultCustom" in installer
    assert "Convert-RimeDefaultCustom -Path $defaultCustom" in installer
    assert "拍台文安裝工具維護" in installer
    # @next 形式必須保持 @next（不能改成明確列表，否則會蓋掉小狼毫內建注音/倉頡）
    assert "以 @next 附加在小狼毫內建清單之後" in installer
    assert "  schema_list/@next {0}:" in installer
    # normalizer 必須跳過自己輸出的區塊註解，否則重跑會在尾段累積（破壞冪等）
    assert "$managedComments" in installer
    call = installer.index("Convert-RimeDefaultCustom -Path $defaultCustom")
    deploy = installer.index("# Step 4: 部署 RIME")
    assert call < deploy


def test_windows_installer_reports_unexpected_errors_with_line_numbers():
    installer = read("install_windows.ps1")

    assert "\ntrap {" in installer
    assert "發生位置" in installer
    assert "PSVersionTable.PSVersion" in installer


def test_readme_documents_boshiamy_install_option():
    readme = read("README.md")

    assert "嘸蝦米" in readme
