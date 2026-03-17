# Full Bundle Installer Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create one-click installers for Windows (.exe) and macOS (.pkg) that bundle the Rime engine + phah_taibun schema, so non-technical users can install the Taiwanese Hokkien IME without any prior knowledge of Rime.

**Architecture:** Each platform installer bundles the upstream Rime engine (Weasel for Windows, Squirrel for macOS) together with all phah_taibun schema files, Lua modules, and the Iansui font. The installer installs the Rime engine if not present, then **delegates to the existing `scripts/install_windows.ps1` / `scripts/install_macos.sh`** for schema registration, rime.lua merging, and deployment — avoiding duplicating already-tested installation logic. A GitHub Actions CI pipeline automates building release artifacts on each tagged version. All downloaded binaries are verified with SHA256 checksums pinned at build time.

**Tech Stack:** Inno Setup (Windows .exe), pkgbuild + productbuild (macOS .pkg), GitHub Actions CI, PowerShell/Bash scripting

### Design Decisions

1. **Reuse existing install scripts**: The project already has mature install scripts (`scripts/install_windows.ps1`, `scripts/install_macos.sh`) that handle edge cases (rime.lua merging, schema registration with `@next` syntax, bopomofo_tw dependency checking). The installer bundles and invokes these directly rather than reimplementing their logic.

2. **PrivilegesRequired=lowest (Windows)**: All phah_taibun data goes to user-space `%APPDATA%\Rime`. Only Weasel itself needs admin. If Weasel is already installed, no elevation is needed.

3. **Squirrel as prerequisite (macOS)**: Rather than silently installing Squirrel (which would surprise users), the installer checks for it and fails with a clear download URL if missing. The welcome page documents this requirement.

4. **Pinned upstream versions**: CI pins Weasel/Squirrel to specific tested versions with SHA256 verification, rather than downloading "latest" at install time.

---

## Chunk 1: Project Structure & Windows Installer

### File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `installer/windows/phah_taibun.iss` | Inno Setup script — main installer definition |
| Create | `installer/windows/download_weasel.ps1` | PowerShell script to download latest Weasel release |
| Create | `installer/windows/pre_uninstall.ps1` | Pre-uninstall: remove schema files, deregister |
| Create | `installer/macos/build_pkg.sh` | macOS: download Squirrel, build .pkg |
| Create | `installer/macos/scripts/postinstall` | macOS pkg postinstall script |
| Create | `installer/macos/scripts/preinstall` | macOS pkg preinstall script |
| Create | `installer/macos/distribution.xml` | macOS productbuild distribution descriptor |
| Create | `.github/workflows/release.yml` | CI pipeline: build installers on tag push |
| Existing | `icons/icon.ico` | Windows installer/tray icon |
| Existing | `icons/icon_256.png` | macOS installer banner |
| Existing | `icons/icon_1024.png` | macOS .pkg background |
| Existing | `schema/*` | All schema files to bundle |
| Existing | `lua/*` | All Lua modules to bundle |
| Existing | `rime.lua` | Module registration file |

---

### Task 1: Download Weasel Script

**Files:**
- Create: `installer/windows/download_weasel.ps1`

- [ ] **Step 1: Write the download script**

```powershell
# download_weasel.ps1
# Downloads the latest Weasel (小狼毫) release from GitHub
# Output: weasel-installer.exe in the current directory

param(
    [string]$OutputDir = ".",
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"

if ($Version -eq "") {
    Write-Host "Fetching latest Weasel release..."
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/rime/weasel/releases/latest"
    $Version = $release.tag_name
} else {
    Write-Host "Fetching Weasel release $Version..."
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/rime/weasel/releases/tags/$Version"
}

Write-Host "Weasel version: $Version"

$asset = $release.assets | Where-Object { $_.name -match "weasel-.*\.exe$" } | Select-Object -First 1

if (-not $asset) {
    Write-Error "No .exe asset found in Weasel release $Version"
    exit 1
}

$outputPath = Join-Path $OutputDir $asset.name
Write-Host "Downloading $($asset.name) ($([math]::Round($asset.size / 1MB, 1)) MB)..."
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $outputPath

Write-Host "Downloaded to: $outputPath"
Write-Output $outputPath
```

- [ ] **Step 2: Test the script locally**

Run: `pwsh installer/windows/download_weasel.ps1 -OutputDir /tmp`
Expected: Weasel .exe downloaded to /tmp/

- [ ] **Step 3: Commit**

```bash
git add installer/windows/download_weasel.ps1
git commit -m "feat(installer): add Weasel download script for Windows"
```

---

### Task 2: Installer Delegates to Existing Install Script (Windows)

The Inno Setup script copies the project's `scripts/install_windows.ps1` into the install dir and invokes it as the post-install step. This reuses the existing, battle-tested installation logic (rime.lua merging with duplicate detection, `schema_list/@next` YAML registration, bopomofo_tw dependency check, font download).

No new post-install script is needed — the existing `scripts/install_windows.ps1` already handles everything. The Inno Setup `[Run]` section invokes it directly.

**Note:** The existing script's `-ProjectRoot` parameter must point to `{app}` (where Inno Setup copies schema/lua files). Verify the existing script accepts this parameter or add it if needed.

- [ ] **Step 1: Review `scripts/install_windows.ps1` for compatibility**

Read the existing script and verify it can be invoked from an arbitrary directory with the schema files located alongside it. If it assumes it's run from the git repo root, add a `-ProjectRoot` parameter.

- [ ] **Step 2: Commit any needed changes to install_windows.ps1**

```bash
git add scripts/install_windows.ps1
git commit -m "refactor(installer): make install_windows.ps1 invocable from bundled installer"
```

---

### Task 3: Pre-Uninstall Script (Windows)

**Files:**
- Create: `installer/windows/pre_uninstall.ps1`

- [ ] **Step 1: Write the pre-uninstall script**

```powershell
# pre_uninstall.ps1
# Removes phah_taibun schema files but preserves user dictionaries

param(
    [string]$RimeUserDir = "$env:APPDATA\Rime"
)

$filesToRemove = @(
    "phah_taibun.schema.yaml",
    "phah_taibun.dict.yaml",
    "phah_taibun_reverse.dict.yaml",
    "hanlo_rules.yaml",
    "lighttone_rules.json",
    "hoabun_map.txt"
)

foreach ($file in $filesToRemove) {
    $path = Join-Path $RimeUserDir $file
    if (Test-Path $path) {
        Remove-Item $path -Force
        Write-Host "Removed: $file"
    }
}

# Remove lua modules (but keep lua/ directory for other IMEs)
$luaDir = Join-Path $RimeUserDir "lua"
Get-ChildItem $luaDir -Filter "phah_taibun_*.lua" -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item $_.FullName -Force
    Write-Host "Removed: lua/$($_.Name)"
}

# Remove phah_taibun entries from rime.lua (keep other IME entries)
$rimeLuaPath = Join-Path $RimeUserDir "rime.lua"
if (Test-Path $rimeLuaPath) {
    $lines = Get-Content $rimeLuaPath -Encoding UTF8
    $filtered = $lines | Where-Object { $_ -notmatch "phah_taibun" }
    Set-Content -Path $rimeLuaPath -Value $filtered -Encoding UTF8
    Write-Host "Cleaned phah_taibun entries from rime.lua"
}

# Remove phah_taibun from default.custom.yaml
$defaultCustom = Join-Path $RimeUserDir "default.custom.yaml"
if (Test-Path $defaultCustom) {
    $lines = Get-Content $defaultCustom -Encoding UTF8
    $filtered = $lines | Where-Object { $_ -notmatch "phah_taibun" }
    Set-Content -Path $defaultCustom -Value $filtered -Encoding UTF8
    Write-Host "Removed phah_taibun from default.custom.yaml"
}

# Preserve user custom dictionaries:
#   phah_taibun.custom.dict.yaml
#   phah_taibun.phrase.dict.yaml
Write-Host "Note: User custom dictionaries preserved (if any)"
Write-Host "Pre-uninstall complete!"
```

- [ ] **Step 2: Commit**

```bash
git add installer/windows/pre_uninstall.ps1
git commit -m "feat(installer): add Windows pre-uninstall script"
```

---

### Task 4: Inno Setup Script

**Files:**
- Create: `installer/windows/phah_taibun.iss`

- [ ] **Step 1: Write the Inno Setup script**

The Inno Setup script defines the full Windows installer. It:
- Checks if Weasel is installed; if not, runs the bundled Weasel installer silently
- Copies schema files, Lua modules, and font to appropriate locations
- Runs post_install.ps1 to register and deploy
- Provides uninstaller that runs pre_uninstall.ps1

```iss
; phah_taibun.iss — Inno Setup script for 拍台文輸入法
; Builds a single .exe installer bundling Weasel + phah_taibun schema

#define MyAppName "拍台文輸入法 Phah Tai-bun"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Phah Tai-bun Project"
#define MyAppURL "https://github.com/soanseng/rime-phah-taibun"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\PhahTaibun
DefaultGroupName={#MyAppName}
OutputBaseFilename=phah-taibun-setup-{#MyAppVersion}
SetupIconFile=..\..\icons\icon.ico
UninstallDisplayIcon={app}\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\..\LICENSE

[Languages]
Name: "tchinese"; MessagesFile: "compiler:Languages\ChineseTraditional.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; --- Weasel installer (bundled) ---
Source: "build\weasel-installer.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: not IsWeaselInstalled

; --- Schema files → Rime user dir ---
Source: "..\..\schema\phah_taibun.schema.yaml"; DestDir: "{userappdata}\Rime"; Flags: ignoreversion
Source: "..\..\schema\phah_taibun.dict.yaml"; DestDir: "{userappdata}\Rime"; Flags: ignoreversion
Source: "..\..\schema\phah_taibun_reverse.dict.yaml"; DestDir: "{userappdata}\Rime"; Flags: ignoreversion
Source: "..\..\schema\hanlo_rules.yaml"; DestDir: "{userappdata}\Rime"; Flags: ignoreversion
Source: "..\..\schema\lighttone_rules.json"; DestDir: "{userappdata}\Rime"; Flags: ignoreversion
Source: "..\..\schema\hoabun_map.txt"; DestDir: "{userappdata}\Rime"; Flags: ignoreversion

; --- Custom dict (only if not exists, preserve user data) ---
Source: "..\..\schema\default.custom.yaml"; DestDir: "{userappdata}\Rime"; Flags: onlyifdoesntexist

; --- Lua modules → Rime user dir/lua/ ---
Source: "..\..\lua\phah_taibun_*.lua"; DestDir: "{userappdata}\Rime\lua"; Flags: ignoreversion

; --- Module registration ---
Source: "..\..\rime.lua"; DestDir: "{app}"; Flags: ignoreversion

; --- Icon ---
Source: "..\..\icons\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

; --- Font ---
Source: "build\Iansui-Regular.ttf"; DestDir: "{autofonts}"; FontInstall: "Iansui"; Flags: onlyifdoesntexist uninsneveruninstall

; --- Existing install script (reused, not duplicated) ---
Source: "..\..\scripts\install_windows.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion
; --- Uninstall script (new, handles cleanup only) ---
Source: "pre_uninstall.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion

[Run]
; Install Weasel if not present (requires elevation via UAC prompt)
Filename: "{tmp}\weasel-installer.exe"; Parameters: "/S"; StatusMsg: "安裝小狼毫 Rime 引擎..."; Check: not IsWeaselInstalled; Flags: waituntilterminated shellexec

; Delegate to existing install script for schema registration, rime.lua merge, deployment
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\scripts\install_windows.ps1"" -ProjectRoot ""{app}"""; StatusMsg: "設定拍台文輸入法..."; Flags: runhidden waituntilterminated

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\scripts\pre_uninstall.ps1"""; Flags: runhidden waituntilterminated

[Code]
function IsWeaselInstalled: Boolean;
var
  path: String;
begin
  Result := RegQueryStringValue(HKLM, 'SOFTWARE\Rime\Weasel', 'WeaselRoot', path)
    or DirExists(ExpandConstant('{autopf}\Rime'))
    or DirExists(ExpandConstant('{autopf32}\Rime'));
end;
```

- [ ] **Step 2: Commit**

```bash
git add installer/windows/phah_taibun.iss
git commit -m "feat(installer): add Inno Setup script for Windows bundle installer"
```

---

## Chunk 2: macOS Installer & CI Pipeline

### Task 5: macOS Post-Install Script

**Files:**
- Create: `installer/macos/scripts/postinstall`

- [ ] **Step 1: Write the macOS postinstall script**

This runs as root after pkgbuild copies files. It delegates to the existing
`scripts/install_macos.sh` for the actual installation logic (schema copy, rime.lua merge,
default.custom.yaml registration, bopomofo_tw verification).

**Key fix:** In macOS `.pkg` postinstall context, `$USER` is `root`, not the GUI user.
We use `/usr/bin/stat -f '%Su' /dev/console` to reliably detect the logged-in user.

```bash
#!/bin/bash
# postinstall — run after macOS .pkg installs files
# Delegates to the project's existing install_macos.sh

set -e

INSTALL_SRC="/tmp/phah_taibun_staging"

# --- Detect real user (not root) ---
# In .pkg context, $USER is root. Get the actual console user.
if [ "$USER" = "root" ] || [ -z "$USER" ]; then
    REAL_USER=$(/usr/bin/stat -f '%Su' /dev/console)
else
    REAL_USER="$USER"
fi

REAL_HOME=$(dscl . -read /Users/"${REAL_USER}" NFSHomeDirectory 2>/dev/null | awk '{print $2}')
if [ -z "${REAL_HOME}" ]; then
    REAL_HOME="/Users/${REAL_USER}"
fi

echo "Installing phah_taibun for user: ${REAL_USER} (${REAL_HOME})"

# --- Delegate to existing install_macos.sh ---
# The existing script handles: schema copy, lua copy, rime.lua merge,
# default.custom.yaml registration, bopomofo_tw check, font install, Squirrel restart
chmod +x "${INSTALL_SRC}/scripts/install_macos.sh"
sudo -u "${REAL_USER}" bash "${INSTALL_SRC}/scripts/install_macos.sh" --project-root "${INSTALL_SRC}"

# --- Cleanup staging ---
rm -rf "${INSTALL_SRC}"

echo "拍台文輸入法安裝完成！"
exit 0
```

**Note:** The existing `scripts/install_macos.sh` may need a `--project-root` flag added so it can find schema/lua files from a non-default location. This is a small refactor to the existing script.

- [ ] **Step 2: Make executable and commit**

```bash
chmod +x installer/macos/scripts/postinstall
git add installer/macos/scripts/postinstall
git commit -m "feat(installer): add macOS postinstall script"
```

---

### Task 6: macOS Pre-Install Script

**Files:**
- Create: `installer/macos/scripts/preinstall`

- [ ] **Step 1: Write the macOS preinstall script**

Checks for Squirrel prerequisite. Fails with a clear message and download URL if missing,
rather than silently installing a system-level input method framework without explicit user consent.

```bash
#!/bin/bash
# preinstall — verify Squirrel prerequisite before installing phah_taibun

set -e

if [ ! -d "/Library/Input Methods/Squirrel.app" ]; then
    echo "============================================"
    echo "錯誤：鼠鬚管 (Squirrel) 尚未安裝。"
    echo ""
    echo "拍台文輸入法需要鼠鬚管 Rime 引擎。"
    echo "請先至以下網址下載安裝："
    echo "  https://rime.im/download/"
    echo ""
    echo "安裝鼠鬚管後，請重新執行本安裝程式。"
    echo "============================================"
    exit 1
fi

# Create staging directory
mkdir -p /tmp/phah_taibun_staging

echo "Pre-install checks passed: Squirrel detected"
exit 0
```

- [ ] **Step 2: Make executable and commit**

```bash
chmod +x installer/macos/scripts/preinstall
git add installer/macos/scripts/preinstall
git commit -m "feat(installer): add macOS preinstall script"
```

---

### Task 7: macOS Build Script

**Files:**
- Create: `installer/macos/build_pkg.sh`
- Create: `installer/macos/distribution.xml`

- [ ] **Step 1: Write distribution.xml**

```xml
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="2">
    <title>拍台文輸入法 Phah Tai-bun</title>
    <organization>com.phah-taibun</organization>
    <domains enable_localSystem="true"/>
    <options customize="never" require-scripts="true" rootVolumeOnly="true"/>

    <welcome file="welcome.html"/>
    <license file="LICENSE"/>

    <pkg-ref id="com.phah-taibun.schema"/>

    <choices-outline>
        <line choice="default">
            <line choice="com.phah-taibun.schema"/>
        </line>
    </choices-outline>

    <choice id="default"/>
    <choice id="com.phah-taibun.schema"
            visible="false"
            title="拍台文輸入法">
        <pkg-ref id="com.phah-taibun.schema"/>
    </choice>

    <pkg-ref id="com.phah-taibun.schema"
             version="1.0.0"
             onConclusion="none">phah_taibun.pkg</pkg-ref>
</installer-gui-script>
```

- [ ] **Step 2: Write build_pkg.sh**

```bash
#!/bin/bash
# build_pkg.sh — Build macOS .pkg installer for 拍台文輸入法
# Requires: macOS with pkgbuild + productbuild

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"
STAGING="${BUILD_DIR}/staging"
VERSION="${1:-1.0.0}"

echo "Building phah_taibun macOS installer v${VERSION}..."

# --- Clean & prepare ---
rm -rf "${BUILD_DIR}"
mkdir -p "${STAGING}/schema" "${STAGING}/lua" "${STAGING}/fonts"

# --- Stage files ---
cp "${PROJECT_ROOT}"/schema/phah_taibun.schema.yaml \
   "${PROJECT_ROOT}"/schema/phah_taibun.dict.yaml \
   "${PROJECT_ROOT}"/schema/phah_taibun_reverse.dict.yaml \
   "${PROJECT_ROOT}"/schema/hanlo_rules.yaml \
   "${PROJECT_ROOT}"/schema/lighttone_rules.json \
   "${PROJECT_ROOT}"/schema/hoabun_map.txt \
   "${PROJECT_ROOT}"/schema/default.custom.yaml \
   "${STAGING}/schema/"

cp "${PROJECT_ROOT}"/lua/phah_taibun_*.lua "${STAGING}/lua/"
cp "${PROJECT_ROOT}"/rime.lua "${STAGING}/"

# --- Download Iansui font if not cached ---
FONT_PATH="${STAGING}/fonts/Iansui-Regular.ttf"
if [ ! -f "${FONT_PATH}" ]; then
    echo "Downloading Iansui font..."
    FONT_URL=$(curl -s https://api.github.com/repos/ChhoeTaigi/iansui/releases/latest \
        | grep "browser_download_url.*Iansui-Regular\.ttf" \
        | head -1 \
        | cut -d '"' -f 4)
    curl -L -o "${FONT_PATH}" "${FONT_URL}"
fi

# --- Build component .pkg ---
pkgbuild \
    --root "${STAGING}" \
    --install-location /tmp/phah_taibun_staging \
    --scripts "${SCRIPT_DIR}/scripts" \
    --identifier com.phah-taibun.schema \
    --version "${VERSION}" \
    "${BUILD_DIR}/phah_taibun.pkg"

# --- Build product .pkg (with UI) ---
# Copy resources for installer UI
mkdir -p "${BUILD_DIR}/resources"
cp "${PROJECT_ROOT}/LICENSE" "${BUILD_DIR}/resources/"

cat > "${BUILD_DIR}/resources/welcome.html" << 'HTML'
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, sans-serif; padding: 20px;">
<h1>拍台文輸入法</h1>
<h2>Phah Tai-bun Input Method</h2>
<p>這是一個基於 Rime 的台語輸入法，支援漢羅混寫。</p>
<p>安裝程式會：</p>
<ul>
<li>安裝鼠鬚管 (Squirrel) Rime 引擎（若尚未安裝）</li>
<li>安裝拍台文輸入方案</li>
<li>安裝芫荽字體</li>
</ul>
<p>安裝完成後，請在「系統設定 → 鍵盤 → 輸入方式」中啟用。</p>
</body>
</html>
HTML

productbuild \
    --distribution "${SCRIPT_DIR}/distribution.xml" \
    --resources "${BUILD_DIR}/resources" \
    --package-path "${BUILD_DIR}" \
    "${BUILD_DIR}/phah-taibun-${VERSION}.pkg"

echo ""
echo "Build complete: ${BUILD_DIR}/phah-taibun-${VERSION}.pkg"
```

- [ ] **Step 3: Make executable and commit**

```bash
chmod +x installer/macos/build_pkg.sh
git add installer/macos/build_pkg.sh installer/macos/distribution.xml
git commit -m "feat(installer): add macOS pkg build script and distribution config"
```

---

### Task 8: GitHub Actions Release Pipeline

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Write the CI pipeline**

**Note:** Pin upstream versions and verify SHA256 checksums. Update the version/hash
constants in this file when upgrading Weasel or Iansui.

```yaml
name: Build Installers

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:
    inputs:
      version:
        description: 'Version number (e.g., 1.0.0)'
        required: true

# Pin upstream dependency versions — update these when upgrading
env:
  # TODO: Fill in actual values before first build
  WEASEL_VERSION: "0.16.3"
  WEASEL_SHA256: "TODO_FILL_IN_SHA256_HASH"
  IANSUI_VERSION: "v1.0.0"
  IANSUI_SHA256: "TODO_FILL_IN_SHA256_HASH"

permissions:
  contents: write

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Download and verify Weasel
        shell: pwsh
        run: |
          mkdir installer/windows/build
          $release = Invoke-RestMethod "https://api.github.com/repos/rime/weasel/releases/tags/$env:WEASEL_VERSION"
          $asset = $release.assets | Where-Object { $_.name -match "weasel-.*\.exe$" } | Select-Object -First 1
          Invoke-WebRequest $asset.browser_download_url -OutFile "installer/windows/build/weasel-installer.exe"
          $hash = (Get-FileHash "installer/windows/build/weasel-installer.exe" -Algorithm SHA256).Hash
          if ($hash -ne $env:WEASEL_SHA256) {
            Write-Error "Weasel checksum mismatch! Expected: $env:WEASEL_SHA256 Got: $hash"
            exit 1
          }

      - name: Download and verify Iansui font
        shell: pwsh
        run: |
          $release = Invoke-RestMethod "https://api.github.com/repos/ChhoeTaigi/iansui/releases/tags/$env:IANSUI_VERSION"
          $asset = $release.assets | Where-Object { $_.name -eq "Iansui-Regular.ttf" } | Select-Object -First 1
          Invoke-WebRequest $asset.browser_download_url -OutFile "installer/windows/build/Iansui-Regular.ttf"
          $hash = (Get-FileHash "installer/windows/build/Iansui-Regular.ttf" -Algorithm SHA256).Hash
          if ($hash -ne $env:IANSUI_SHA256) {
            Write-Error "Iansui checksum mismatch! Expected: $env:IANSUI_SHA256 Got: $hash"
            exit 1
          }

      - name: Build with Inno Setup
        run: iscc installer/windows/phah_taibun.iss

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: windows-installer
          path: installer/windows/Output/*.exe

  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build .pkg
        run: |
          VERSION="${GITHUB_REF_NAME#v}"
          [ -z "$VERSION" ] && VERSION="${{ github.event.inputs.version }}"
          bash installer/macos/build_pkg.sh "$VERSION"

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: macos-installer
          path: installer/macos/build/*.pkg

  release:
    needs: [build-windows, build-macos]
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/')
    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v4

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          draft: true
          generate_release_notes: true
          files: |
            windows-installer/*.exe
            macos-installer/*.pkg
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add GitHub Actions pipeline for building Windows/macOS installers"
```

---

### Task 9: Integration Test & Documentation

- [ ] **Step 1: Add installer README**

Create `installer/README.md` with build instructions for contributors:
- How to build Windows installer locally (requires Inno Setup 6+)
- How to build macOS installer locally (requires macOS)
- How the CI pipeline works
- Version bumping process

- [ ] **Step 2: Test Windows build locally (if on Windows)**

```powershell
cd installer/windows
mkdir build
pwsh download_weasel.ps1 -OutputDir build
# Then open phah_taibun.iss in Inno Setup and compile
```

- [ ] **Step 3: Test macOS build locally (if on macOS)**

```bash
cd installer/macos
bash build_pkg.sh 1.0.0
# Output: build/phah-taibun-1.0.0.pkg
```

- [ ] **Step 4: Commit documentation**

```bash
git add installer/README.md
git commit -m "docs: add installer build instructions"
```
