# Full Bundle Installer Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Create one-click installers for Windows (.exe) and macOS (.pkg) that bundle the Rime engine + phah_taibun schema, so non-technical users can install the Taiwanese Hokkien IME without any prior knowledge of Rime.

**Architecture:** Each platform installer bundles the upstream Rime engine (Weasel for Windows, Squirrel for macOS) together with all phah_taibun schema files, Lua modules, and the Iansui font. The installer installs the Rime engine if not present, then **delegates to the existing `scripts/install_windows.ps1` / `scripts/install_macos.sh`** for schema registration, rime.lua merging, and deployment — avoiding duplicating already-tested installation logic. A GitHub Actions CI pipeline automates building release artifacts on each tagged version. All downloaded binaries are verified with SHA256 checksums pinned at build time.

**Tech Stack:** Inno Setup (Windows .exe), pkgbuild + productbuild (macOS .pkg), GitHub Actions CI, PowerShell/Bash scripting

### Design Decisions

1. **Reuse existing install scripts via staging**: The project already has mature install scripts (`scripts/install_windows.ps1`, `scripts/install_macos.sh`) that handle edge cases (rime.lua merging, schema registration with `@next` syntax, bopomofo_tw dependency checking). The installer stages files in standard project layout (`schema/`, `lua/`, `rime.lua`), then invokes the install script with `--project-root` pointing to the staging area. **No file copying is done by the installer directly to the Rime user directory** — the install script handles everything.

2. **PrivilegesRequired=admin (Windows)**: Weasel installation needs admin rights. After Weasel installs, a post-install verification step checks it actually succeeded (handles UAC denial gracefully). If Weasel was already installed, the admin right is technically unnecessary but harmless.

3. **Squirrel as prerequisite (macOS)**: Rather than silently installing Squirrel (which would surprise users), the installer checks for it and fails with a clear download URL if missing. The welcome page documents this as a prerequisite.

4. **Pinned upstream versions**: CI pins Weasel/Squirrel to specific tested versions with SHA256 verification, rather than downloading "latest" at install time.

5. **Post-install verification**: Both Windows and macOS installers verify the Rime engine is present after the installation step, before proceeding to schema registration. This prevents broken installs where the engine is missing but schema files are partially configured.

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

- [x] **Step 1: Write the download script**

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

- [x] **Step 2: Test the script locally**

Run: `pwsh installer/windows/download_weasel.ps1 -OutputDir /tmp`
Expected: Weasel .exe downloaded to /tmp/

- [x] **Step 3: Commit**

```bash
git add installer/windows/download_weasel.ps1
git commit -m "feat(installer): add Weasel download script for Windows"
```

---

### Task 2: Install Scripts Accept -ProjectRoot / --project-root

All three install scripts (`install_windows.ps1`, `install_macos.sh`, `install_linux.sh`) have been refactored to accept an optional parameter that overrides the default `PROJ_DIR` derivation. When called from a bundle installer, the parameter points to the staging directory where schema/lua/rime.lua files are arranged in the standard project layout.

**Already done:**
- [x] `install_windows.ps1` accepts `-ProjectRoot "C:\path"` parameter
- [x] `install_macos.sh` accepts `--project-root /path` parameter
- [x] `install_linux.sh` accepts `--project-root /path` parameter (consistency)
- All scripts fall back to deriving from script location if parameter is omitted

**Design:** The bundle installer stages files in `{app}/` using the standard project layout (`{app}/schema/`, `{app}/lua/`, `{app}/rime.lua`), then invokes the install script with `-ProjectRoot "{app}"`. The install script handles all file copying to Rime user dir, rime.lua merging, schema registration, and deployment — no duplication.

- [x] **Step 1: Committed**

```bash
git add scripts/install_windows.ps1 scripts/install_macos.sh scripts/install_linux.sh
git commit -m "refactor(installer): add --project-root parameter to all install scripts"
```

---

### Task 3: Pre-Uninstall Script (Windows)

**Files:**
- Create: `installer/windows/pre_uninstall.ps1`

- [x] **Step 1: Write the pre-uninstall script**

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

- [x] **Step 2: Commit**

```bash
git add installer/windows/pre_uninstall.ps1
git commit -m "feat(installer): add Windows pre-uninstall script"
```

---

### Task 4: Inno Setup Script

**Files:**
- Create: `installer/windows/phah_taibun.iss`

- [x] **Step 1: Write the Inno Setup script**

The Inno Setup script defines the full Windows installer. Key design:
- **Staging approach**: All schema/lua/rime.lua files are staged under `{app}/` in standard project layout (`{app}/schema/`, `{app}/lua/`, `{app}/rime.lua`). The existing `install_windows.ps1` is invoked with `-ProjectRoot "{app}"` to handle all file copying to Rime user dir, rime.lua merging, schema registration, and deployment. **No files are copied directly to `{userappdata}\Rime` by Inno Setup** — this prevents dual-copy conflicts.
- **Post-Weasel verification**: After Weasel installer runs, a Pascal Script check verifies Weasel actually installed before proceeding. If UAC was denied or installation failed, the installer aborts with a clear message rather than creating a broken install.
- **Privilege model**: `PrivilegesRequired=admin` since Weasel needs admin. If Weasel is already installed, the phah_taibun files go to user-space only.

```iss
; phah_taibun.iss — Inno Setup script for 拍台文輸入法
; Builds a single .exe installer bundling Weasel + phah_taibun schema
;
; Architecture: Inno Setup stages files under {app}/ in standard project layout.
; The existing install_windows.ps1 is invoked with -ProjectRoot "{app}" to handle
; all file operations to the Rime user directory. This avoids duplicating logic.

#define MyAppName "拍台文輸入法 Phah Tai-bun"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Phah Tai-bun Project"
#define MyAppURL "https://github.com/soanseng/rime-phah-taibun"

[Setup]
; TODO: Generate a real GUID before first build: powershell [System.Guid]::NewGuid()
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
; Weasel needs admin; schema install is user-space but we need admin for Weasel
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\..\LICENSE

[Languages]
Name: "tchinese"; MessagesFile: "compiler:Languages\ChineseTraditional.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; --- Weasel installer (bundled, extracted to temp) ---
Source: "build\weasel-installer.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: not IsWeaselInstalled

; --- Stage schema files under {app}/schema/ (standard project layout) ---
; install_windows.ps1 will copy these to %APPDATA%\Rime via -ProjectRoot
Source: "..\..\schema\phah_taibun.schema.yaml"; DestDir: "{app}\schema"; Flags: ignoreversion
Source: "..\..\schema\phah_taibun.dict.yaml"; DestDir: "{app}\schema"; Flags: ignoreversion
Source: "..\..\schema\phah_taibun.phrase.dict.yaml"; DestDir: "{app}\schema"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\..\schema\phah_taibun.custom.dict.yaml"; DestDir: "{app}\schema"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\..\schema\phah_taibun_reverse.dict.yaml"; DestDir: "{app}\schema"; Flags: ignoreversion
Source: "..\..\schema\hanlo_rules.yaml"; DestDir: "{app}\schema"; Flags: ignoreversion
Source: "..\..\schema\lighttone_rules.json"; DestDir: "{app}\schema"; Flags: ignoreversion
Source: "..\..\schema\hoabun_map.txt"; DestDir: "{app}\schema"; Flags: ignoreversion
Source: "..\..\schema\default.custom.yaml"; DestDir: "{app}\schema"; Flags: ignoreversion

; --- Stage Lua modules under {app}/lua/ ---
Source: "..\..\lua\phah_taibun_*.lua"; DestDir: "{app}\lua"; Flags: ignoreversion

; --- Module registration file at {app}/rime.lua ---
Source: "..\..\rime.lua"; DestDir: "{app}"; Flags: ignoreversion

; --- Icon ---
Source: "..\..\icons\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

; --- Font (installed directly to user fonts, not staged) ---
Source: "build\Iansui-Regular.ttf"; DestDir: "{autofonts}"; FontInstall: "Iansui"; Flags: onlyifdoesntexist uninsneveruninstall

; --- Install + uninstall scripts ---
Source: "..\..\scripts\install_windows.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "pre_uninstall.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion

[Run]
; Install Weasel if not present (runs with admin via UAC)
Filename: "{tmp}\weasel-installer.exe"; Parameters: "/S"; StatusMsg: "安裝小狼毫 Rime 引擎..."; Check: not IsWeaselInstalled; Flags: waituntilterminated shellexec

; Verify Weasel is installed before proceeding (handles UAC denial)
; This check is done in [Code] CurStepChanged(ssPostInstall)

; Delegate ALL file operations to existing install script
; -ProjectRoot points to {app} where files are staged in standard layout
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\scripts\install_windows.ps1"" -ProjectRoot ""{app}"""; StatusMsg: "設定拍台文輸入法..."; Flags: runhidden waituntilterminated; Check: IsWeaselInstalled

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

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    { Verify Weasel is actually installed after the Weasel installer step }
    if not IsWeaselInstalled then
    begin
      MsgBox('小狼毫 (Weasel) 安裝失敗或已取消。' + #13#10 +
             '拍台文輸入法需要小狼毫 Rime 引擎才能運作。' + #13#10 + #13#10 +
             '請手動安裝小狼毫後，重新執行本安裝程式：' + #13#10 +
             'https://rime.im/download/',
             mbError, MB_OK);
      WizardForm.Close;
    end;
  end;
end;
```

- [x] **Step 2: Commit**

```bash
git add installer/windows/phah_taibun.iss
git commit -m "feat(installer): add Inno Setup script for Windows bundle installer"
```

---

## Chunk 2: macOS Installer & CI Pipeline

### Task 5: macOS Post-Install Script

**Files:**
- Create: `installer/macos/scripts/postinstall`

- [x] **Step 1: Write the macOS postinstall script**

This runs as root after pkgbuild copies files. It delegates to the existing
`scripts/install_macos.sh` (which now accepts `--project-root`) for the actual
installation logic (schema copy, rime.lua merge, default.custom.yaml registration,
bopomofo_tw verification, font install, Squirrel restart).

**Key design choices:**
- Uses `scutil` for reliable console user detection (Apple-recommended approach, works
  with Fast User Switching, remote sessions, etc.)
- Staging directory uses `/private/var/tmp/` (mode 700) instead of world-writable `/tmp`
  to prevent TOCTOU attacks
- `install_macos.sh` already accepts `--project-root` (refactored in Task 2)

```bash
#!/bin/bash
# postinstall — run after macOS .pkg installs files
# Delegates to the project's existing install_macos.sh

set -e

INSTALL_SRC="/private/var/tmp/phah_taibun_staging"

# --- Detect real user (not root) ---
# In .pkg context, $USER is root. Use scutil (Apple-recommended approach)
# to reliably detect the logged-in GUI user.
REAL_USER=$(scutil <<< "show State:/Users/ConsoleUser" | awk '/Name :/ && ! /loginwindow/ { print $3 }')

if [ -z "${REAL_USER}" ] || [ "${REAL_USER}" = "root" ]; then
    echo "錯誤：無法偵測目前登入的使用者" >&2
    exit 1
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

- [x] **Step 2: Make executable and commit**

```bash
chmod +x installer/macos/scripts/postinstall
git add installer/macos/scripts/postinstall
git commit -m "feat(installer): add macOS postinstall script"
```

---

### Task 6: macOS Pre-Install Script

**Files:**
- Create: `installer/macos/scripts/preinstall`

- [x] **Step 1: Write the macOS preinstall script**

Checks for Squirrel prerequisite. Fails with a clear message and download URL if missing,
rather than silently installing a system-level input method framework without explicit user consent.

Uses `/private/var/tmp/` for staging (not world-writable `/tmp`) with restrictive permissions.

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

# Create staging directory with restrictive permissions (prevent TOCTOU)
STAGING="/private/var/tmp/phah_taibun_staging"
rm -rf "${STAGING}"
mkdir -p "${STAGING}"
chmod 700 "${STAGING}"

echo "Pre-install checks passed: Squirrel detected"
exit 0
```

- [x] **Step 2: Make executable and commit**

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

- [x] **Step 1: Write distribution.xml**

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

- [x] **Step 2: Write build_pkg.sh**

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
mkdir -p "${STAGING}/schema" "${STAGING}/lua" "${STAGING}/scripts" "${STAGING}/fonts"

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

# Stage install script (postinstall delegates to it)
cp "${PROJECT_ROOT}"/scripts/install_macos.sh "${STAGING}/scripts/"

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
    --install-location /private/var/tmp/phah_taibun_staging \
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
<li>需要已安裝鼠鬚管 (Squirrel) Rime 引擎（<a href="https://rime.im/download/">下載</a>）</li>
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

- [x] **Step 3: Make executable and commit**

```bash
chmod +x installer/macos/build_pkg.sh
git add installer/macos/build_pkg.sh installer/macos/distribution.xml
git commit -m "feat(installer): add macOS pkg build script and distribution config"
```

---

### Task 8: GitHub Actions Release Pipeline

**Files:**
- Create: `.github/workflows/release.yml`

- [x] **Step 1: Write the CI pipeline**

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

- [x] **Step 2: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add GitHub Actions pipeline for building Windows/macOS installers"
```

---

### Task 9: Integration Test & Documentation

- [x] **Step 1: Add installer README**

Create `installer/README.md` with build instructions for contributors:
- How to build Windows installer locally (requires Inno Setup 6+)
- How to build macOS installer locally (requires macOS)
- How the CI pipeline works
- Version bumping process

- [x] **Step 2: Test Windows build locally (if on Windows)**

```powershell
cd installer/windows
mkdir build
pwsh download_weasel.ps1 -OutputDir build
# Then open phah_taibun.iss in Inno Setup and compile
```

- [x] **Step 3: Test macOS build locally (if on macOS)**

```bash
cd installer/macos
bash build_pkg.sh 1.0.0
# Output: build/phah-taibun-1.0.0.pkg
```

- [x] **Step 4: Commit documentation**

```bash
git add installer/README.md
git commit -m "docs: add installer build instructions"
```
