# 拍台文 Phah Tai-bun 自動安裝工具 (Windows / 小狼毫 Weasel)
# 使用方式：在專案目錄中執行 powershell -ExecutionPolicy Bypass -File scripts\install_windows.ps1
# 從 bundle installer 呼叫時：powershell ... -ProjectRoot "C:\path\to\staged\files"

param(
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

# 專案根目錄：優先使用 -ProjectRoot 參數，否則從腳本位置推算
if ($ProjectRoot -ne "" -and (Test-Path $ProjectRoot)) {
    $PROJ_DIR = (Resolve-Path $ProjectRoot).Path
} else {
    $PROJ_DIR = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
}

# 小狼毫路徑
$RIME_DIR = "$env:APPDATA\Rime"
$FONT_DIR = "$env:LOCALAPPDATA\Microsoft\Windows\Fonts"
$WEASEL_DIR = "${env:ProgramFiles(x86)}\Rime\weasel-*"
$WEASEL_DIR_ALT = "$env:ProgramFiles\Rime\weasel-*"

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
# Step 0: 偵測環境
# ============================================================
if (-not (Test-Path $RIME_DIR)) {
    # 嘗試建立 Rime 資料夾（第一次安裝可能不存在）
    $weaselExists = (Get-Item $WEASEL_DIR -ErrorAction SilentlyContinue) -or
                    (Get-Item $WEASEL_DIR_ALT -ErrorAction SilentlyContinue)
    if (-not $weaselExists) {
        Write-Host "警告：找不到小狼毫安裝，但仍會安裝檔案到 $RIME_DIR" -ForegroundColor Yellow
        Write-Host "請先安裝小狼毫：https://rime.im/download/" -ForegroundColor Yellow
        Write-Host ""
    }
}

Write-Host "Rime 資料夾：$RIME_DIR" -ForegroundColor Green
Write-Host ""

Write-Host "本工具將執行以下作業："
Write-Host "  1. 複製方案檔到 Rime 資料夾"
Write-Host "  2. 複製 Lua 腳本到 Rime 資料夾"
Write-Host "  3. 安裝芫荽 iansui 字體"
Write-Host ""
Write-Host "※ 若有自訂設定尚未備份，請按 Ctrl+C 終止" -ForegroundColor Yellow
Write-Host ""

# ============================================================
# 偵測現有方案
# ============================================================
Write-Host "[ 偵測現有方案 ]" -ForegroundColor Green
Write-Host ""

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
    Write-Host "拍台文只會安裝 phah_taibun_* 檔案，不會覆蓋現有方案" -ForegroundColor Green
} else {
    Write-Host "未偵測到現有方案（首次安裝）"
}
Write-Host ""

# 檢查 default.custom.yaml
$needRegister = $true
if (Test-Path "$RIME_DIR\default.custom.yaml") {
    if (Select-String -Path "$RIME_DIR\default.custom.yaml" -Pattern "phah_taibun" -Quiet) {
        $needRegister = $false
        Write-Host "default.custom.yaml 已含 phah_taibun 方案，跳過註冊" -ForegroundColor Green
    } else {
        Write-Host "偵測到現有的 default.custom.yaml，將追加拍台文方案" -ForegroundColor Yellow
    }
}

# ============================================================
# Step 1: 複製方案檔
# ============================================================
Write-Host ""
Write-Host "[ Step 1: 複製方案檔 ]" -ForegroundColor Green
Write-Host ""

New-Item -ItemType Directory -Force -Path $RIME_DIR | Out-Null

$schemaFiles = @(
    "phah_taibun.schema.yaml",
    "phah_taibun.dict.yaml",
    "phah_taibun_reverse.dict.yaml",
    "hanlo_rules.yaml",
    "lighttone_rules.json",
    "hoabun_map.txt"
)

foreach ($file in $schemaFiles) {
    $src = Join-Path $PROJ_DIR "schema\$file"
    if (Test-Path $src) {
        Copy-Item -Force $src "$RIME_DIR\$file"
        Write-Host "  [ok] $file" -ForegroundColor Green
    } else {
        Write-Host "  [miss] $file" -ForegroundColor Red
    }
}

# 使用者自訂字典：只在不存在時複製
foreach ($file in @("phah_taibun.custom.dict.yaml", "phah_taibun.phrase.dict.yaml")) {
    $src = Join-Path $PROJ_DIR "schema\$file"
    $dest = "$RIME_DIR\$file"
    if ((Test-Path $src) -and -not (Test-Path $dest)) {
        Copy-Item $src $dest
        Write-Host "  [ok] $file (首次安裝)" -ForegroundColor Green
    } elseif ((Test-Path $src) -and (Test-Path $dest)) {
        Write-Host "  [保留] $file (已有使用者資料)" -ForegroundColor Yellow
    }
}

# ============================================================
# Step 2: 複製 Lua 腳本
# ============================================================
Write-Host ""
Write-Host "[ Step 2: 複製 Lua 腳本 ]" -ForegroundColor Green
Write-Host ""

New-Item -ItemType Directory -Force -Path "$RIME_DIR\lua" | Out-Null

$luaCount = 0
Get-ChildItem "$PROJ_DIR\lua\phah_taibun_*.lua" -ErrorAction SilentlyContinue | ForEach-Object {
    Copy-Item -Force $_.FullName "$RIME_DIR\lua\$($_.Name)"
    Write-Host "  [ok] $($_.Name)" -ForegroundColor Green
    $luaCount++
}

if ($luaCount -eq 0) {
    Write-Host "  [skip] 沒有找到 Lua 腳本" -ForegroundColor Yellow
}

# 合併 rime.lua
$rimeLuaSrc = Join-Path $PROJ_DIR "rime.lua"
$rimeLuaDest = "$RIME_DIR\rime.lua"

if (Test-Path $rimeLuaSrc) {
    if (Test-Path $rimeLuaDest) {
        Copy-Item -Force $rimeLuaDest "$RIME_DIR\rime.lua.bak"
        Write-Host "  [備份] rime.lua -> rime.lua.bak" -ForegroundColor Yellow

        $existingContent = Get-Content $rimeLuaDest -Raw -ErrorAction SilentlyContinue
        $merged = 0
        Get-Content $rimeLuaSrc | ForEach-Object {
            $line = $_
            if ($line -match '^\s*$' -or $line -match '^\s*--') { return }
            if ($existingContent -notlike "*$line*") {
                Add-Content -Path $rimeLuaDest -Value $line
                $merged++
            }
        }
        if ($merged -gt 0) {
            Write-Host "  [ok] rime.lua (追加 $merged 個模組)" -ForegroundColor Green
        } else {
            Write-Host "  [ok] rime.lua (模組已註冊)" -ForegroundColor Green
        }
    } else {
        Copy-Item -Force $rimeLuaSrc $rimeLuaDest
        Write-Host "  [ok] rime.lua (模組註冊)" -ForegroundColor Green
    }
}

# ============================================================
# Step 2.5: 註冊方案到 default.custom.yaml
# ============================================================
if ($needRegister) {
    $defaultCustom = "$RIME_DIR\default.custom.yaml"
    if (Test-Path $defaultCustom) {
        Copy-Item -Force $defaultCustom "$RIME_DIR\default.custom.yaml.bak"
        Write-Host "  [備份] default.custom.yaml -> default.custom.yaml.bak" -ForegroundColor Yellow

        $content = Get-Content $defaultCustom -Raw
        if ($content -match '- schema:') {
            # 在最後一個 schema 行之後追加
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
        Write-Host "  [ok] 已將 phah_taibun 追加到 default.custom.yaml" -ForegroundColor Green
    } else {
        $src = Join-Path $PROJ_DIR "schema\default.custom.yaml"
        Copy-Item -Force $src $defaultCustom
        Write-Host "  [ok] default.custom.yaml (新建)" -ForegroundColor Green
    }
}

# ============================================================
# Step 3: 安裝字體
# ============================================================
Write-Host ""
Write-Host "[ Step 3: 安裝芫荽 iansui 字體 ]" -ForegroundColor Green
Write-Host ""

New-Item -ItemType Directory -Force -Path $FONT_DIR | Out-Null

$fontPath = "$FONT_DIR\Iansui-Regular.ttf"
if (Test-Path $fontPath) {
    Write-Host "  [ok] 芫荽 iansui 字體 (已安裝)" -ForegroundColor Green
} else {
    Write-Host "  正在下載芫荽 iansui 字體..."
    try {
        $iansui_url = "https://github.com/ChhoeTaigi/iansui/releases/latest/download/Iansui-Regular.ttf"
        Invoke-WebRequest -Uri $iansui_url -OutFile $fontPath | Out-Null
        Write-Host "  [ok] 芫荽 iansui 字體已安裝到 $FONT_DIR" -ForegroundColor Green
    } catch {
        Write-Host "  [warn] 無法下載，請手動安裝：" -ForegroundColor Yellow
        Write-Host "         https://github.com/ChhoeTaigi/iansui/releases"
    }
}

# ============================================================
# Step 4: 部署提示
# ============================================================
Write-Host ""
Write-Host "[ Step 4: 部署 RIME ]" -ForegroundColor Green
Write-Host ""
Write-Host "請手動重新部署小狼毫：" -ForegroundColor Yellow
Write-Host "  右鍵點擊系統匣的小狼毫圖示 -> 重新部署" -ForegroundColor Yellow
Write-Host ""

# ============================================================
# 安裝完成
# ============================================================
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  拍台文 Phah Tai-bun 安裝完成！" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Rime 資料夾：$RIME_DIR"
Write-Host ""
Write-Host "已安裝："
Write-Host "  - 方案檔：$($schemaFiles.Count) 個"
Write-Host "  - Lua 腳本：$luaCount 個 (皆為 phah_taibun_* 命名)"
Write-Host ""

# 顯示可用方案
Write-Host "可用的輸入方案："
Get-ChildItem "$RIME_DIR\*.schema.yaml" -ErrorAction SilentlyContinue | ForEach-Object {
    $name = $_.BaseName -replace '\.schema$', ''
    if ($name -eq "phah_taibun") {
        Write-Host "  * $name (拍台文) <- 新安裝" -ForegroundColor Green
    } else {
        Write-Host "  * $name"
    }
}
Write-Host ""
Write-Host "切換輸入法：Ctrl+`` 或 F4"
Write-Host ""

# 字體設定提示
$weaselCustom = "$RIME_DIR\weasel.custom.yaml"
if ((Test-Path $weaselCustom) -and (Select-String -Path $weaselCustom -Pattern "iansui" -Quiet -CaseSensitive:$false)) {
    # 已設定
} else {
    Write-Host "【字體設定】" -ForegroundColor Yellow
    Write-Host "  建議在 $weaselCustom 加入以下設定："
    Write-Host ""
    Write-Host "    patch:" -ForegroundColor Green
    Write-Host "      style/font_face: `"Iansui`"" -ForegroundColor Green
    Write-Host "      style/font_point: 14" -ForegroundColor Green
    Write-Host ""
    Write-Host "  儲存後重新部署即可生效。"
    Write-Host ""
}

Write-Host "如遇問題，請到 GitHub 回報："
Write-Host "  https://github.com/soanseng/rime-phah-taibun"
Write-Host ""
