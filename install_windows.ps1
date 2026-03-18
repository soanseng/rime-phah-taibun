# 拍台文 Phah Tai-bun 自動安裝工具 (Windows / 小狼毫 Weasel)
# 參考 ryanwuson/rime-liur 安裝腳本架構
# https://github.com/soanseng/rime-phah-taibun

$ErrorActionPreference = "Stop"

# GitHub 相關設定
$GITHUB_REPO = "soanseng/rime-phah-taibun"
$GITHUB_BRANCH = "main"
$GITHUB_API = "https://api.github.com/repos/$GITHUB_REPO/git/trees/$GITHUB_BRANCH`?recursive=1"
$GITHUB_RAW = "https://raw.githubusercontent.com/$GITHUB_REPO/$GITHUB_BRANCH"

# 設定路徑
$RIME_DIR = "$env:APPDATA\Rime"
$FONT_DIR = "$env:LOCALAPPDATA\Microsoft\Windows\Fonts"
$WEASEL_DIR = "${env:ProgramFiles(x86)}\Rime\weasel-*"
$WEASEL_DIR_ALT = "$env:ProgramFiles\Rime\weasel-*"

# 使用者自訂檔案（保留不覆蓋）
$CUSTOM_FILES = @("phah_taibun.custom.dict.yaml", "phah_taibun.phrase.dict.yaml")

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
Write-Host "  1. 從 GitHub 下載拍台文方案檔案"
Write-Host "  2. 註冊輸入方案"
Write-Host "  3. 安裝芫荽 iansui 字體"
Write-Host ""
Write-Host "Rime 資料夾：$RIME_DIR" -ForegroundColor Green
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
# 從 GitHub 取得檔案清單
# ============================================================
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

# 分類檔案
$SCHEMA_FILES = @()
$LUA_FILES = @()
$HAS_RIME_LUA = $false

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
        Invoke-WebRequest -Uri "$GITHUB_RAW/$file" -OutFile "$RIME_DIR\$filename" | Out-Null
    }
}

# 下載 lua/ 檔案
foreach ($file in $LUA_FILES) {
    $current++
    $filename = Split-Path $file -Leaf
    Show-Progress -Current $current -Total $TOTAL -FileName $filename
    Invoke-WebRequest -Uri "$GITHUB_RAW/$file" -OutFile "$RIME_DIR\lua\$filename" | Out-Null
}

# 下載 rime.lua（合併既有）
if ($HAS_RIME_LUA) {
    $current++
    $rimeLuaDest = "$RIME_DIR\rime.lua"

    if (Test-Path $rimeLuaDest) {
        Show-Progress -Current $current -Total $TOTAL -FileName "rime.lua [合併]"
        Copy-Item -Force $rimeLuaDest "$RIME_DIR\rime.lua.bak"

        $tmpFile = "$env:TEMP\phah_taibun_rime.lua"
        Invoke-WebRequest -Uri "$GITHUB_RAW/rime.lua" -OutFile $tmpFile | Out-Null

        $existingContent = Get-Content $rimeLuaDest -Raw -ErrorAction SilentlyContinue
        Get-Content $tmpFile | ForEach-Object {
            $line = $_
            if ($line -match '^\s*$' -or $line -match '^\s*--') { return }
            if ($existingContent -notlike "*$line*") {
                Add-Content -Path $rimeLuaDest -Value $line
            }
        }
        Remove-Item $tmpFile -ErrorAction SilentlyContinue
    } else {
        Show-Progress -Current $current -Total $TOTAL -FileName "rime.lua"
        Invoke-WebRequest -Uri "$GITHUB_RAW/rime.lua" -OutFile $rimeLuaDest | Out-Null
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
        # 下載預設的 default.custom.yaml
        Invoke-WebRequest -Uri "$GITHUB_RAW/schema/default.custom.yaml" -OutFile $defaultCustom | Out-Null
        Write-Host "  default.custom.yaml（新建）" -ForegroundColor Green
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
    try {
        $iansui_url = "https://raw.githubusercontent.com/ButTaiwan/iansui/main/fonts/ttf/Iansui-Regular.ttf"
        Invoke-WebRequest -Uri $iansui_url -OutFile $fontPath | Out-Null
        Write-Host "  芫荽字體已安裝" -ForegroundColor Green
    } catch {
        Write-Host "  無法下載，請手動安裝：" -ForegroundColor Yellow
        Write-Host "  https://github.com/ButTaiwan/iansui/releases" -ForegroundColor Cyan
    }
}

# ============================================================
# Step 4: 部署提示
# ============================================================
Write-Host ""
Write-Host "[ Step 4: 部署 RIME ]" -ForegroundColor Green
Write-Host ""
Write-Host "請手動重新部署小狼毫（右鍵點擊系統匣圖示 → 重新部署）" -ForegroundColor Yellow

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

Write-Host "更多資訊：https://github.com/$GITHUB_REPO"
Write-Host ""
