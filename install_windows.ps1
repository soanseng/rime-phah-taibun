# 拍台文 Phah Tai-bun 自動安裝工具 (Windows / 小狼毫 Weasel)
# 參考 ryanwuson/rime-liur 安裝腳本架構
# https://github.com/soanseng/rime-phah-taibun

param(
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

# 發行資產固定版本；命令列安裝只下載該版本的完整封存檔。
$RELEASE_VERSION = "0.3.1"
$RELEASE_BASE = "https://github.com/soanseng/rime-phah-taibun/releases/download/v$RELEASE_VERSION"
$SOURCE_ARCHIVE_URL = "$RELEASE_BASE/PhahTaiBun-source.zip"
$SOURCE_ARCHIVE_SHA256_URL = "$RELEASE_BASE/PhahTaiBun-source.zip.sha256"

# 設定路徑
$RIME_DIR = "$env:APPDATA\Rime"
$FONT_DIR = "$env:LOCALAPPDATA\Microsoft\Windows\Fonts"
$WEASEL_DIR = "${env:ProgramFiles(x86)}\Rime\weasel-*"
$WEASEL_DIR_ALT = "$env:ProgramFiles\Rime\weasel-*"

# 使用者自訂檔案（保留不覆蓋）
$CUSTOM_FILES = @("phah_taibun.custom.dict.yaml", "phah_taibun.phrase.dict.yaml")

function Get-VerifiedReleasePayload {
    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("PhahTaiBun-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
    $archive = Join-Path $tempRoot "PhahTaiBun-source.zip"
    $checksum = Join-Path $tempRoot "PhahTaiBun-source.zip.sha256"
    $sourceRoot = Join-Path $tempRoot "source"

    try {
        Invoke-WebRequest -Uri $SOURCE_ARCHIVE_URL -OutFile $archive | Out-Null
        Invoke-WebRequest -Uri $SOURCE_ARCHIVE_SHA256_URL -OutFile $checksum | Out-Null
        $expected = ((Get-Content $checksum | Select-Object -First 1) -split '\s+')[0].ToUpperInvariant()
        $actual = (Get-FileHash -Path $archive -Algorithm SHA256).Hash.ToUpperInvariant()
        if ($expected -notmatch '^[0-9A-F]{64}$' -or $actual -ne $expected) {
            throw "PhahTaiBun-source.zip SHA-256 驗證失敗。"
        }
        Expand-Archive -Path $archive -DestinationPath $sourceRoot -Force
        return @{ Root = $sourceRoot; Temp = $tempRoot }
    } catch {
        Remove-Item -Recurse -Force $tempRoot -ErrorAction SilentlyContinue
        throw
    }
}

# 打包安裝器傳入內建 payload；命令列安裝下載固定版本並驗證封存檔。
$USE_LOCAL_PAYLOAD = $true
$DOWNLOADED_PAYLOAD = $false
$TEMP_SOURCE_DIR = ""
if ($ProjectRoot -ne "") {
    $resolvedRoot = Resolve-Path $ProjectRoot -ErrorAction SilentlyContinue
    $resolvedRootPath = if ($resolvedRoot) { $resolvedRoot.Path } else { "" }
    if ($resolvedRoot -and
        (Test-Path (Join-Path $resolvedRootPath "schema")) -and
        (Test-Path (Join-Path $resolvedRootPath "lua"))) {
        $ProjectRoot = $resolvedRootPath
    } else {
        Write-Host "錯誤：指定的 ProjectRoot 沒有 schema/ 與 lua/：$ProjectRoot" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "正在下載並驗證拍台文 v$RELEASE_VERSION 完整安裝資產..."
    $payload = Get-VerifiedReleasePayload
    $ProjectRoot = $payload.Root
    $TEMP_SOURCE_DIR = $payload.Temp
    $DOWNLOADED_PAYLOAD = $true
}

# 進度條函數（from rime-liur）
function Show-Progress {
    param(
        [int]$Current,
        [int]$Total,
        [string]$FileName
    )
    $width = 20
    $filled = [math]::Floor($Current * $width / $Total)
    $empty = $width - $filled
    $bar = ([char]0x2588).ToString() * $filled + ([char]0x2591).ToString() * $empty
    if ($FileName.Length -gt 40) {
        $FileName = $FileName.Substring(0, 37) + "..."
    }
    $status = "  [$bar] $("{0,3}" -f $Current)/$Total  $($FileName.PadRight(45))"
    Write-Host "`r$status" -NoNewline
}

function Copy-OrDownload {
    param(
        [string]$SourcePath,
        [string]$DestinationPath
    )

    Copy-Item -Force (Join-Path $ProjectRoot $SourcePath) $DestinationPath
}

# ============================================================
# 標題
# ============================================================
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  拍台文 Phah Tai-bun 自動安裝工具" -ForegroundColor Cyan
Write-Host "  (Windows / 小狼毫 Weasel)" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# Step 0: 偵測小狼毫
# ============================================================
$weaselExists = (Get-Item $WEASEL_DIR -ErrorAction SilentlyContinue) -or
                (Get-Item $WEASEL_DIR_ALT -ErrorAction SilentlyContinue) -or
                (Test-Path $RIME_DIR)
if (-not $weaselExists) {
    Write-Host "錯誤：找不到小狼毫 (Weasel) 安裝" -ForegroundColor Red
    Write-Host ""
    Write-Host "拍台文需要小狼毫 Rime 輸入法引擎才能運作。" -ForegroundColor Yellow
    Write-Host "請先下載並安裝小狼毫，安裝完成後再執行本腳本。" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  下載頁面：https://rime.im/download/" -ForegroundColor Cyan
    Write-Host "  GitHub：  https://github.com/rime/weasel/releases" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "安裝步驟："
    Write-Host "  1. 下載 weasel-x.x.x.x-installer.exe"
    Write-Host "  2. 執行安裝程式（需要系統管理員權限）"
    Write-Host "  3. 安裝完成後重新執行本腳本"
    Write-Host ""
    exit 1
}

Write-Host "本工具將執行以下作業："
if ($DOWNLOADED_PAYLOAD) {
    Write-Host "  1. 從已驗證的 v$RELEASE_VERSION 封存檔安裝拍台文方案"
} else {
    Write-Host "  1. 從安裝包內建檔案安裝拍台文方案"
}
Write-Host "  2. 註冊輸入方案"
Write-Host "  3. 安裝芫荽 iansui 字體"
Write-Host ""
Write-Host "Rime 資料夾：$RIME_DIR" -ForegroundColor Green
Write-Host "安裝來源：$ProjectRoot" -ForegroundColor Green
Write-Host ""

# 偵測現有方案
$existingSchemas = @()
if (Test-Path $RIME_DIR) {
    Get-ChildItem "$RIME_DIR\*.schema.yaml" -ErrorAction SilentlyContinue | ForEach-Object {
        $name = $_.BaseName -replace '\.schema$', ''
        $existingSchemas += $name
    }
}
if ($existingSchemas.Count -gt 0) {
    Write-Host "已安裝的輸入方案："
    foreach ($s in $existingSchemas) {
        Write-Host "  * $s"
    }
    Write-Host ""
}

# ============================================================
# 取得檔案清單
# ============================================================
$SCHEMA_FILES = @()
$LUA_FILES = @()
$HAS_RIME_LUA = $false

if ($USE_LOCAL_PAYLOAD) {
    Write-Host "正在讀取安裝包內建檔案清單..."
    Get-ChildItem (Join-Path $ProjectRoot "schema") -File | ForEach-Object {
        if ($_.Name -ne "default.custom.yaml") {
            $SCHEMA_FILES += "schema/$($_.Name)"
        }
    }
    Get-ChildItem (Join-Path $ProjectRoot "lua") -Filter "phah_taibun_*.lua" -File | ForEach-Object {
        $LUA_FILES += "lua/$($_.Name)"
    }
    $HAS_RIME_LUA = Test-Path (Join-Path $ProjectRoot "rime.lua")
} else {
    Write-Host "正在從 GitHub 取得檔案清單..."
    try {
        $response = Invoke-RestMethod -Uri $GITHUB_API -Method Get
    } catch {
        Write-Host "錯誤：GitHub API 連線失敗" -ForegroundColor Red
        Write-Host "       請檢查網路連線，或稍後再試"
        Write-Host "       https://github.com/$GITHUB_REPO"
        exit 1
    }

    if (-not $response.tree) {
        Write-Host "錯誤：無法解析檔案清單" -ForegroundColor Red
        exit 1
    }

    foreach ($item in $response.tree) {
        if ($item.type -ne "blob") { continue }
        $path = $item.path

        if ($path -match "^schema/.+" -and $path -notmatch "default\.custom\.yaml$") {
            $SCHEMA_FILES += $path
        } elseif ($path -match "^lua/phah_taibun_.*\.lua$") {
            $LUA_FILES += $path
        } elseif ($path -eq "rime.lua") {
            $HAS_RIME_LUA = $true
        }
    }
}

$TOTAL = $SCHEMA_FILES.Count + $LUA_FILES.Count + $(if ($HAS_RIME_LUA) { 1 } else { 0 })
Write-Host "找到 $($SCHEMA_FILES.Count) 個方案檔案、$($LUA_FILES.Count) 個 Lua 模組"
Write-Host ""

# ============================================================
# Step 1: 下載方案檔案
# ============================================================
Write-Host "[ Step 1: 下載拍台文方案檔案 ]" -ForegroundColor Green

New-Item -ItemType Directory -Force -Path $RIME_DIR | Out-Null
New-Item -ItemType Directory -Force -Path "$RIME_DIR\lua" | Out-Null

$current = 0

# 下載 schema/ 檔案到 Rime 根目錄
foreach ($file in $SCHEMA_FILES) {
    $current++
    $filename = Split-Path $file -Leaf

    if ($CUSTOM_FILES -contains $filename -and (Test-Path "$RIME_DIR\$filename")) {
        Show-Progress -Current $current -Total $TOTAL -FileName "$filename [保留]"
    } else {
        Show-Progress -Current $current -Total $TOTAL -FileName $filename
        Copy-OrDownload -SourcePath $file -DestinationPath "$RIME_DIR\$filename"
    }
}

# 下載 lua/ 檔案
foreach ($file in $LUA_FILES) {
    $current++
    $filename = Split-Path $file -Leaf
    Show-Progress -Current $current -Total $TOTAL -FileName $filename
    Copy-OrDownload -SourcePath $file -DestinationPath "$RIME_DIR\lua\$filename"
}

# 下載 rime.lua（合併既有）
if ($HAS_RIME_LUA) {
    $current++
    $rimeLuaDest = "$RIME_DIR\rime.lua"

    if (Test-Path $rimeLuaDest) {
        Show-Progress -Current $current -Total $TOTAL -FileName "rime.lua [合併]"
        Copy-Item -Force $rimeLuaDest "$RIME_DIR\rime.lua.bak"

        if ($USE_LOCAL_PAYLOAD) {
            $tmpFile = Join-Path $ProjectRoot "rime.lua"
        } else {
            $tmpFile = "$env:TEMP\phah_taibun_rime.lua"
            Invoke-WebRequest -Uri "$GITHUB_RAW/rime.lua" -OutFile $tmpFile | Out-Null
        }

        $existingContent = Get-Content $rimeLuaDest -Raw -ErrorAction SilentlyContinue
        Get-Content $tmpFile | ForEach-Object {
            $line = $_
            if ($line -match '^\s*$' -or $line -match '^\s*--') { return }
            if ($existingContent -notlike "*$line*") {
                Add-Content -Path $rimeLuaDest -Value $line
            }
        }
        if (-not $USE_LOCAL_PAYLOAD) {
            Remove-Item $tmpFile -ErrorAction SilentlyContinue
        }
    } else {
        Show-Progress -Current $current -Total $TOTAL -FileName "rime.lua"
        Copy-OrDownload -SourcePath "rime.lua" -DestinationPath $rimeLuaDest
    }
}

Write-Host ""

# ============================================================
# Step 2: 註冊方案到 default.custom.yaml
# ============================================================
Write-Host ""
Write-Host "[ Step 2: 註冊輸入方案 ]" -ForegroundColor Green

$defaultCustom = "$RIME_DIR\default.custom.yaml"
$needRegister = $true

if (Test-Path $defaultCustom) {
    if (Select-String -Path $defaultCustom -Pattern "phah_taibun" -Quiet) {
        $needRegister = $false
        Write-Host "  default.custom.yaml 已含 phah_taibun，跳過" -ForegroundColor Green
    }
}

if ($needRegister) {
    if (Test-Path $defaultCustom) {
        Copy-Item -Force $defaultCustom "$RIME_DIR\default.custom.yaml.bak"

        $content = Get-Content $defaultCustom -Raw
        if ($content -match '- schema:') {
            $lines = Get-Content $defaultCustom
            $lastIdx = -1
            for ($i = 0; $i -lt $lines.Count; $i++) {
                if ($lines[$i] -match '- schema:') { $lastIdx = $i }
            }
            if ($lastIdx -ge 0) {
                $indent = $lines[$lastIdx] -replace '- schema:.*', ''
                $newLine = "${indent}- schema: phah_taibun"
                $newLines = $lines[0..$lastIdx] + $newLine + $lines[($lastIdx+1)..($lines.Count-1)]
                $newLines | Set-Content $defaultCustom -Encoding UTF8
            }
        } else {
            Add-Content -Path $defaultCustom -Value "`n  schema_list/@next:`n    schema: phah_taibun"
        }
        Write-Host "  已將 phah_taibun 追加到 default.custom.yaml" -ForegroundColor Green
    } else {
        # 安裝預設的 default.custom.yaml
        Copy-OrDownload -SourcePath "schema/default.custom.yaml" -DestinationPath $defaultCustom
        Write-Host "  default.custom.yaml（新建）" -ForegroundColor Green
    }
}

# ============================================================
# Step 2.5: save_options — 記住 F4 選過的 TL/POJ、漢羅/全羅
# ============================================================
if (Test-Path $defaultCustom) {
    if (-not (Select-String -Path $defaultCustom -Pattern "poj_mode" -Quiet)) {
        $lines = Get-Content $defaultCustom
        $newLines = foreach ($line in $lines) {
            $line
            if ($line -match '^patch:') {
                "  switcher/save_options/@before 0: poj_mode"
                "  switcher/save_options/@next: full_romanization"
            }
        }
        $newLines | Set-Content $defaultCustom -Encoding UTF8
        Write-Host "  已將 poj_mode / full_romanization 加入 save_options（記住模式選擇）" -ForegroundColor Green
    }
}

# ============================================================
# Step 3: 安裝芫荽字體
# ============================================================
Write-Host ""
Write-Host "[ Step 3: 安裝芫荽 iansui 字體 ]" -ForegroundColor Green

New-Item -ItemType Directory -Force -Path $FONT_DIR | Out-Null

$fontPath = "$FONT_DIR\Iansui-Regular.ttf"
if (Test-Path $fontPath) {
    Write-Host "  芫荽字體（已安裝）" -ForegroundColor Green
} else {
    Write-Host "  正在下載芫荽 iansui 字體..."
    $iansuiRevision = "9d9a8e68bf1e138dd91e562eeff28d95bca33196"
    $iansuiSha256 = "7f1aa62e9dcbf40d0ce41a5d3f1e5ea602e66c295778ac6fefb6b84d8ed08bd5"
    $iansuiUrl = "https://raw.githubusercontent.com/ButTaiwan/iansui/$iansuiRevision/fonts/ttf/Iansui-Regular.ttf"
    $fontTemp = "$fontPath.download"
    try {
        Invoke-WebRequest -Uri $iansuiUrl -OutFile $fontTemp | Out-Null
        $fontHash = (Get-FileHash -Path $fontTemp -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($fontHash -ne $iansuiSha256) {
            throw "Iansui-Regular.ttf SHA-256 驗證失敗。"
        }
        Move-Item -Force $fontTemp $fontPath
        Write-Host "  芫荽字體已驗證並安裝" -ForegroundColor Green
    } catch {
        Remove-Item -Force $fontTemp -ErrorAction SilentlyContinue
        Write-Host "  字體下載或 SHA-256 驗證失敗，請手動安裝：" -ForegroundColor Yellow
        Write-Host "  https://github.com/ButTaiwan/iansui/releases" -ForegroundColor Cyan
    }
}

# ============================================================
# Step 4: 部署 RIME
# ============================================================
Write-Host ""
Write-Host "[ Step 4: 部署 RIME ]" -ForegroundColor Green
Write-Host ""

$weaselInstall = Get-ChildItem -Path @($WEASEL_DIR, $WEASEL_DIR_ALT) -Directory -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
$deployer = if ($weaselInstall) { Join-Path $weaselInstall.FullName "WeaselDeployer.exe" } else { "" }
if (-not $deployer -or -not (Test-Path $deployer)) {
    Write-Host "部署失敗：找不到 WeaselDeployer.exe。" -ForegroundColor Red
    Write-Host "請在小狼毫系統匣選單按「重新部署」，或執行：<小狼毫安裝目錄>\WeaselDeployer.exe /deploy" -ForegroundColor Yellow
    exit 1
}

$deployProcess = Start-Process -FilePath $deployer -ArgumentList "/deploy" -Wait -PassThru
if ($deployProcess.ExitCode -ne 0) {
    Write-Host "部署失敗：WeaselDeployer.exe 結束碼為 $($deployProcess.ExitCode)。" -ForegroundColor Red
    Write-Host "請修正上方錯誤後重試：`"$deployer`" /deploy" -ForegroundColor Yellow
    exit 1
}
Write-Host "已重新部署小狼毫。" -ForegroundColor Green

# ============================================================
# 安裝完成
# ============================================================
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  拍台文 Phah Tai-bun 安裝完成！" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Rime 資料夾：$RIME_DIR"
Write-Host "字體資料夾：$FONT_DIR"
Write-Host ""

# 顯示可用方案
Write-Host "可用的輸入方案："
Get-ChildItem "$RIME_DIR\*.schema.yaml" -ErrorAction SilentlyContinue | ForEach-Object {
    $name = $_.BaseName -replace '\.schema$', ''
    if ($name -eq "phah_taibun") {
        Write-Host "  * $name (拍台文)" -ForegroundColor Green
    } else {
        Write-Host "  * $name"
    }
}
Write-Host ""

# 字體設定提示
$weaselCustom = "$RIME_DIR\weasel.custom.yaml"
if (-not (Test-Path $weaselCustom) -or -not (Select-String -Path $weaselCustom -Pattern "iansui" -Quiet -CaseSensitive:$false)) {
    Write-Host "【字體設定】建議在 weasel.custom.yaml 加入：" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  patch:" -ForegroundColor Green
    Write-Host "    style/font_face: `"Iansui`"" -ForegroundColor Green
    Write-Host "    style/font_point: 14" -ForegroundColor Green
    Write-Host ""
}

if ($TEMP_SOURCE_DIR -and (Test-Path $TEMP_SOURCE_DIR)) {
    Remove-Item -Recurse -Force $TEMP_SOURCE_DIR
}
Write-Host "更多資訊：https://github.com/soanseng/rime-phah-taibun"
Write-Host ""
