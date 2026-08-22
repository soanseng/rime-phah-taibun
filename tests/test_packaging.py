from pathlib import Path

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
    assert "-ProjectRoot" in iss
    assert "PrivilegesRequired=lowest" in iss
    assert "DefaultDirName={localappdata}\\Phah Tai-bun" in iss
    assert "Exec(" in iss
    assert "ewWaitUntilTerminated" in iss
    assert "ResultCode <> 0" in iss
    assert "RaiseException" in iss
    assert "postinstall" not in iss
    assert "param(" in installer
    assert "$ProjectRoot" in installer
    assert "Copy-OrDownload" in installer
    assert 'Copy-OrDownload -SourcePath "schema/default.custom.yaml" -DestinationPath $defaultCustom' in installer


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


def test_release_version_is_consistent_across_runtime_and_packaging_metadata():
    version = "0.4.1"

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
    for package_job in ("package-source", "package-macos", "package-windows"):
        assert jobs[package_job]["needs"] == "verify"


def test_packaging_docs_warn_about_rime_engine_dependency():
    windows_doc = read("packaging/windows/README.md")
    mac_doc = read("packaging/macos/README.md")
    user_doc = read("docs/packaged-installers.md")

    assert "Weasel" in windows_doc
    assert "Squirrel" in mac_doc
    assert "不會覆蓋" in windows_doc
    assert "不會覆蓋" in mac_doc
    assert "PhahTaiBunSetup.exe" in user_doc
    assert "PhahTaiBun.pkg" in user_doc


def test_release_workflow_attaches_packaged_installers():
    workflow = read(".github/workflows/release.yml")

    assert "package-macos" in workflow
    assert "package-windows" in workflow
    assert "packaging/macos/build-pkg.sh" in workflow
    assert "Inno Setup 6\\ISCC.exe" in workflow
    assert "PhahTaiBun.pkg" in workflow
    assert "PhahTaiBunSetup.exe" in workflow


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
    assert "PhahTaiBun.pkg" in packaged
    assert "自訂詞庫" in guide
    assert "重新部署" in guide
