from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


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
    assert "tar -xzf" in installer
    assert "trap cleanup EXIT" in installer


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
