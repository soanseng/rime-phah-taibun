# 拍台文 Phah Tai-bun 自動安裝工具 (Windows / 小狼毫 Weasel)
# 參考 ryanwuson/rime-liur 安裝腳本架構
# https://github.com/soanseng/rime-phah-taibun
#
# 本檔刻意「不帶 BOM」：GitHub raw 的內容會連 BOM 一起交給 iex，而 iex 會把 BOM
# 黏進第一個 token（註解與 param 都會解析失敗，PS 5.1/7 皆然）。因此：
#   1. 單行安裝用 `irm <url> | iex`（本檔無 BOM，可正常解析）
#   2. 打包安裝器改用 -Command + ReadAllText(UTF8) 後 iex（見 phah-taibun.iss）
#   3. 沒有頂層 param()：參數走環境變數或 $args（iex 下沒有參數綁定）
$ProjectRoot = ""
$Schemas = ""
if ($env:PHAH_TAIBUN_PROJECT_ROOT) { $ProjectRoot = "$env:PHAH_TAIBUN_PROJECT_ROOT" }
if ($env:PHAH_TAIBUN_SCHEMAS) { $Schemas = "$env:PHAH_TAIBUN_SCHEMAS" }
for ($i = 0; $i -lt $args.Count; $i++) {
    switch ("$($args[$i])") {
        "-ProjectRoot" { if ($i + 1 -lt $args.Count) { $ProjectRoot = "$($args[$i + 1])"; $i++ } }
        "-Schemas" { if ($i + 1 -lt $args.Count) { $Schemas = "$($args[$i + 1])"; $i++ } }
    }
}

$ErrorActionPreference = "Stop"

# 本腳本自己畫進度條；Invoke-WebRequest 的原生進度條會與它交錯，且在
# Windows PowerShell 5.1 會讓每個下載慢上數倍（嘸蝦米需要 100+ 個檔案）。
$ProgressPreference = "SilentlyContinue"

# 任何未預期的終止錯誤：印出錯誤訊息、行號與 PowerShell 版本，方便使用者回報；
# 不影響既有 try/catch（嘸蝦米、字體）與各步驟的 exit 流程。
trap {
    Write-Host ""
    Write-Host "安裝失敗：$($_.Exception.Message)" -ForegroundColor Red
    $errLine = "$($_.InvocationInfo.Line)".Trim()
    if ($errLine.Length -gt 120) { $errLine = $errLine.Substring(0, 120) + "..." }
    Write-Host "發生位置：第 $($_.InvocationInfo.ScriptLineNumber) 行：$errLine" -ForegroundColor Red
    Write-Host "PowerShell 版本：$($PSVersionTable.PSVersion)" -ForegroundColor Red
    Write-Host "請將上方完整輸出（含行號）貼到 GitHub Issues：https://github.com/soanseng/rime-phah-taibun/issues" -ForegroundColor Yellow
    exit 1
}

# 互動模式＝命令列安裝（irm | iex），必須在 $ProjectRoot 被填成解壓目錄前判定；
# 打包安裝器（PhahTaiBunSetup.exe）以 -ProjectRoot 非互動執行，不顯示任何提示。
$INTERACTIVE = ($ProjectRoot -eq "")

# 發行資產版本（後備值）：命令列安裝會先查 GitHub 最新 release，
# 查詢失敗或被網路擋下時才使用此固定版本。
$RELEASE_VERSION = "0.8.0"
$RELEASE_BASE = "https://github.com/soanseng/rime-phah-taibun/releases/download/v$RELEASE_VERSION"
$SOURCE_ARCHIVE_URL = "$RELEASE_BASE/PhahTaiBun-source.zip"
$SOURCE_ARCHIVE_SHA256_URL = "$RELEASE_BASE/PhahTaiBun-source.zip.sha256"

# 嘸蝦米（rime-liur）來源：公開 fork，含 librime 1.16+/Lua 5.4+ 相容修正。
$LIUR_REPO = "soanseng/rime-liur-arch"
$LIUR_BRANCH = "main"
$LIUR_API = "https://api.github.com/repos/$LIUR_REPO/git/trees/$LIUR_BRANCH`?recursive=1"
$LIUR_RAW = "https://raw.githubusercontent.com/$LIUR_REPO/$LIUR_BRANCH"

# 設定路徑
$RIME_DIR = "$env:APPDATA\Rime"
$FONT_DIR = "$env:LOCALAPPDATA\Microsoft\Windows\Fonts"
$WEASEL_DIR = "${env:ProgramFiles(x86)}\Rime\weasel-*"
$WEASEL_DIR_ALT = "$env:ProgramFiles\Rime\weasel-*"

# 使用者自訂檔案（保留不覆蓋）
$CUSTOM_FILES = @("phah_taibun.custom.dict.yaml", "phah_taibun.phrase.dict.yaml")

# Windows PowerShell 5.1 預設把追加文字寫成 UTF-16，UTF8 編碼旗標還會加 BOM。
# 兩者都會讓既有 default.custom.yaml 解析失敗，小狼毫退回內建預設方案。
function Read-RimeText {
    param([string]$Path)
    $reader = New-Object System.IO.StreamReader($Path, $true)
    try { return $reader.ReadToEnd() } finally { $reader.Dispose() }
}

function Write-RimeText {
    param([string]$Path, [string]$Text)
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, $Text, $utf8)
}

function Add-RimeText {
    param([string]$Path, [string]$Text)
    $utf8 = New-Object System.Text.UTF8Encoding $false
    $existing = ""
    if (Test-Path $Path) { $existing = Read-RimeText $Path }
    if ($existing.Length -gt 0 -and -not $existing.EndsWith("`n")) { $Text = "`n" + $Text }
    if (-not $Text.EndsWith("`n")) { $Text = $Text + "`n" }
    [System.IO.File]::AppendAllText($Path, $Text, $utf8)
}

function Get-RimeLines {
    param([string]$Path)
    $text = Read-RimeText $Path
    if ([string]::IsNullOrEmpty($text)) { return @() }
    return ($text -replace "`r`n", "`n" -replace "`r", "`n").TrimEnd("`n").Split("`n")
}

function Test-RimeUtf16 {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $false }
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) { return $true }
    $sample = [Math]::Min(400, $bytes.Length)
    $nul = 0
    for ($i = 0; $i -lt $sample; $i++) { if ($bytes[$i] -eq 0) { $nul++ } }
    return ($sample -gt 8 -and $nul -gt ($sample / 4))
}

function Repair-RimeTextEncoding {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    $name = [System.IO.Path]::GetFileName($Path)
    if (Test-RimeUtf16 $Path) {
        $bak = "$Path.bak"
        if ((Test-Path $bak) -and -not (Test-RimeUtf16 $bak)) {
            Copy-Item -Force $bak $Path
            Write-Host "  $name 曾被寫成 UTF-16，已從 .bak 還原既有方案" -ForegroundColor Yellow
        } else {
            Write-Host "錯誤：$name 編碼已壞，且沒有可用的 .bak。" -ForegroundColor Red
            Write-Host "請先還原原本的 Rime 設定，再重跑安裝。安裝只會追加拍台文，不會取代方案清單。" -ForegroundColor Yellow
            exit 1
        }
    }
}

# PowerShell 的降冪範圍會反向取值：$lines[4..3] 會回傳索引 4 與 3（把檔尾重複一次）。
# 最後一筆方案剛好是檔尾時，尾段必須是空陣列。
function Get-RimeTail {
    param([string[]]$Lines, [int]$AfterIndex)
    if ($AfterIndex + 1 -le $Lines.Count - 1) { return $Lines[($AfterIndex + 1)..($Lines.Count - 1)] }
    return @()
}

# 列出 default.custom.yaml 內註冊的方案 id（涵蓋 - schema: 與 schema_list/@next 兩種形式，去重、依出現順序）。
function Get-RimeSchemaIds {
    param([string]$Path)
    $ids = @()
    $lines = @(Get-RimeLines $Path)
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '^\s*- schema:\s*(\S+)\s*$') {
            if ($ids -notcontains $Matches[1]) { $ids += $Matches[1] }
        }
        elseif ($lines[$i] -match '^\s*schema_list/@next(\s+\d+)?:\s*$' -and
                $i + 1 -lt $lines.Count -and $lines[$i + 1] -match '^\s+schema:\s*(\S+)\s*$') {
            if ($ids -notcontains $Matches[1]) { $ids += $Matches[1] }
            $i++
        }
    }
    return $ids
}

# 把安裝工具管理的 default.custom.yaml 整理成乾淨排版並加上說明註解。
# 只處理 patch: 單一 map 格式；__patch: 複合格式與其他檔案原封不動。
# 使用者自己的設定（menu、key_binder、自訂註解…）會原樣保留在正規化區塊之後。
function Convert-RimeDefaultCustom {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    $lines = @(Get-RimeLines $Path)
    if ($lines.Count -eq 0) { return }

    $bodyStart = 0
    while ($bodyStart -lt $lines.Count -and $lines[$bodyStart] -match '^\s*(#|$)') { $bodyStart++ }
    if ($bodyStart -ge $lines.Count -or $lines[$bodyStart] -notmatch '^patch:\s*$') { return }

    $schemaIds = @(Get-RimeSchemaIds -Path $Path)
    $hasSaveOptions = $false
    $isDashList = $false
    foreach ($line in $lines) {
        if ($line -match 'switcher/save_options') { $hasSaveOptions = $true }
        if ($line -match '^\s*- schema:') { $isDashList = $true }
    }

    $out = New-Object System.Collections.Generic.List[string]
    $out.Add("# default.custom.yaml — 拍台文安裝工具維護")
    $out.Add("#")
    $out.Add("# 安裝工具只會「追加」設定，不會覆蓋小狼毫內建方案與你的其他設定；")
    $out.Add("# 每次安裝前，原始內容都會備份成 default.custom.yaml.backup-<時間戳>。")
    $out.Add("#")
    $out.Add("# schema_list：可用的輸入方案，順序＝F4 選單順序。")
    if ($hasSaveOptions) {
        $out.Add("# switcher/save_options：記住 F4 選過的 TL/POJ、漢羅/全羅，重新部署或重開機不用重選。")
    }
    $out.Add("")
    $out.Add("patch:")

    if ($hasSaveOptions) {
        $out.Add("  # 記住 F4 的輸出模式選擇")
        $out.Add("  switcher/save_options/@before 0: poj_mode")
        $out.Add("  switcher/save_options/@next: full_romanization")
    }

    if ($schemaIds.Count -gt 0) {
        if ($isDashList) {
            $out.Add("  # 輸入方案清單（明確列表：以此為準，小狼毫內建方案不會出現在 F4）；要增刪方案就增減下面幾行。")
            $out.Add("  schema_list:")
            foreach ($id in $schemaIds) { $out.Add("    - schema: $id") }
        } else {
            $out.Add("  # 以下方案以 @next 附加在小狼毫內建清單之後（內建注音、倉頡等仍可用）；新增方案建議重跑安裝工具。")
            $out.Add("  schema_list/@next:")
            $out.Add("    schema: " + $schemaIds[0])
            for ($i = 1; $i -lt $schemaIds.Count; $i++) {
                $out.Add(("  schema_list/@next {0}:" -f $i))
                $out.Add("    schema: " + $schemaIds[$i])
            }
        }
    }

    # 正規化自己輸出的區塊註解：重跑時要跳過，否則會在尾段累積（破壞冪等）
    $managedComments = @(
        "  # 記住 F4 的輸出模式選擇",
        "  # 輸入方案清單（明確列表",
        "  # 以下方案以 @next"
    )

    # 原檔中非安裝工具管理的行（menu、key_binder、自訂註解…）原樣接在後面
    $seenPatch = $false
    $leading = $true
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        if ($leading) {
            if ($line -match '^\s*(#|$)') { continue }
            $leading = $false
        }
        if (-not $seenPatch) {
            if ($line -match '^patch:\s*$') { $seenPatch = $true }
            continue
        }
        $isManagedComment = $false
        foreach ($mc in $managedComments) {
            if ($line.StartsWith($mc)) { $isManagedComment = $true; break }
        }
        if ($isManagedComment) { continue }
        if ($line -match '^\s*- schema:\s*(\S+)\s*$') { continue }
        if ($isDashList -and $line -match '^\s*schema_list:\s*$') { continue }
        if ($line -match '^\s*schema_list/@next(\s+\d+)?:\s*$') {
            if ($i + 1 -lt $lines.Count -and $lines[$i + 1] -match '^\s+schema:\s*(\S+)\s*$') { $i++ }
            continue
        }
        if ($line -match 'switcher/save_options') { continue }
        $out.Add($line)
    }

    Write-RimeText -Path $Path -Text (($out -join "`n") + "`n")
}

# 追加單一方案到 default.custom.yaml，支援三種檔案格式，且已存在就不重複：
# patch: 單一 map（追加到最後一筆 - schema: 之後）、__patch: 列表、@next 形式。
function Add-SchemaEntry {
    param([string]$SchemaId)

    if (Select-String -Path $defaultCustom -Pattern ("schema: " + $SchemaId + "\s*$") -Quiet) {
        return
    }

    $content = Read-RimeText $defaultCustom
    if ($content -match '- schema:') {
        $lines = @(Get-RimeLines $defaultCustom)
        $lastIdx = -1
        for ($i = 0; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -match '^\s*- schema:') { $lastIdx = $i }
        }
        if ($lastIdx -ge 0) {
            $indent = $lines[$lastIdx] -replace '- schema:.*', ''
            $newLines = @($lines[0..$lastIdx] + "${indent}- schema: $SchemaId" + (Get-RimeTail -Lines $lines -AfterIndex $lastIdx))
            Write-RimeText -Path $defaultCustom -Text (($newLines -join "`n") + "`n")
            return
        }
    }

    # 同一個 @next key 在同一份 YAML 只能出現一次，否則後者會覆蓋前者
    # （librime 1.13 實測：重複的 schema_list/@next 只保留最後一筆），故取未占用的序號。
    $nextKey = "schema_list/@next"
    $nextIdx = 1
    while (Select-String -Path $defaultCustom -Pattern ("^\s*" + [regex]::Escape($nextKey) + "\s*:") -Quiet) {
        $nextKey = "schema_list/@next $nextIdx"
        $nextIdx++
    }

    if ((Get-RimeLines $defaultCustom | Select-Object -First 1) -match '^__patch:') {
        Add-RimeText -Path $defaultCustom -Text "  - patch/+:`n      ${nextKey}:`n        schema: $SchemaId"
    } else {
        Add-RimeText -Path $defaultCustom -Text "  ${nextKey}:`n    schema: $SchemaId"
    }
}

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
    # 單行安裝：自動跟隨 GitHub 最新 release（查詢失敗就退回上方固定版本）。
    try {
        $latestRelease = Invoke-RestMethod -Uri "https://api.github.com/repos/soanseng/rime-phah-taibun/releases/latest" -Method Get -TimeoutSec 10
        if ($latestRelease.tag_name -match '^v(\d+\.\d+\.\d+)$') { $RELEASE_VERSION = $Matches[1] }
    } catch { }
    $RELEASE_BASE = "https://github.com/soanseng/rime-phah-taibun/releases/download/v$RELEASE_VERSION"
    $SOURCE_ARCHIVE_URL = "$RELEASE_BASE/PhahTaiBun-source.zip"
    $SOURCE_ARCHIVE_SHA256_URL = "$RELEASE_BASE/PhahTaiBun-source.zip.sha256"
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

# ============================================================
# Step 0.5: 選擇要安裝的輸入方案
# ============================================================
if ($Schemas -eq "" -and -not $INTERACTIVE) { $Schemas = "phah" }
if ($Schemas -eq "" -or $Schemas -eq "both") {
    $INSTALL_PHAH = $true
    $INSTALL_LIUR = $true
} elseif ($Schemas -eq "liur") {
    $INSTALL_PHAH = $false
    $INSTALL_LIUR = $true
} elseif ($Schemas -eq "phah") {
    $INSTALL_PHAH = $true
    $INSTALL_LIUR = $false
} else {
    Write-Host "錯誤：-Schemas 必須是 phah、liur 或 both（目前：$Schemas）" -ForegroundColor Red
    exit 1
}

if ($INTERACTIVE) {
    Write-Host "請選擇要安裝的輸入方案：" -ForegroundColor Yellow
    Write-Host "  1. 拍台文（台語）"
    Write-Host "  2. 嘸蝦米（rime-liur）"
    Write-Host "  3. 拍台文 + 嘸蝦米（預設）"
    $schemaChoice = Read-Host "請輸入選項 (1/2/3，Enter=3)"
    if ($schemaChoice -eq "1") {
        $INSTALL_PHAH = $true
        $INSTALL_LIUR = $false
    } elseif ($schemaChoice -eq "2") {
        $INSTALL_PHAH = $false
        $INSTALL_LIUR = $true
    } else {
        $INSTALL_PHAH = $true
        $INSTALL_LIUR = $true
    }
    Write-Host ""
}

Write-Host "本工具將執行以下作業："
if ($INSTALL_PHAH) {
    if ($DOWNLOADED_PAYLOAD) {
        Write-Host "  1. 從已驗證的 v$RELEASE_VERSION 封存檔安裝拍台文方案"
    } else {
        Write-Host "  1. 從安裝包內建檔案安裝拍台文方案"
    }
    Write-Host "  2. 註冊輸入方案"
    Write-Host "  3. 安裝芫荽 iansui 字體"
}
if ($INSTALL_LIUR) {
    Write-Host "  4. 下載並安裝嘸蝦米（rime-liur，來源 soanseng/rime-liur-arch）"
}
if ($INTERACTIVE) {
    Write-Host "  5. 先備份原設定，再詢問要保留哪些既有輸入法（可保留注音）"
}
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

if (-not $INSTALL_PHAH) {
    $SCHEMA_FILES = @()
    $LUA_FILES = @()
    $HAS_RIME_LUA = $false
    Write-Host "略過拍台文方案檔案（僅安裝嘸蝦米）" -ForegroundColor Yellow
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

        $existingContent = Read-RimeText $rimeLuaDest
        Get-RimeLines $tmpFile | ForEach-Object {
            $line = $_
            if ($line -match '^\s*$' -or $line -match '^\s*--') { return }
            if ($existingContent -notlike "*$line*") {
                Add-RimeText -Path $rimeLuaDest -Text $line
                $existingContent = $existingContent + "`n" + $line
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

# 變動任何設定前先備份原設定（時間戳備份，不覆蓋先前的備份檔）。
if (Test-Path "$RIME_DIR\default.custom.yaml") {
    $backupStamp = Get-Date -Format "yyyyMMdd-HHmmss"
    Copy-Item -Force "$RIME_DIR\default.custom.yaml" "$RIME_DIR\default.custom.yaml.backup-$backupStamp"
    Write-Host "  已備份原設定：default.custom.yaml.backup-$backupStamp" -ForegroundColor Green
}

Repair-RimeTextEncoding "$RIME_DIR\default.custom.yaml"
Repair-RimeTextEncoding "$RIME_DIR\rime.lua"

$defaultCustom = "$RIME_DIR\default.custom.yaml"
$needRegister = $true

if (Test-Path $defaultCustom) {
    if (Select-String -Path $defaultCustom -Pattern "phah_taibun" -Quiet) {
        $needRegister = $false
        Write-Host "  default.custom.yaml 已含 phah_taibun，跳過" -ForegroundColor Green
    }
}

if (-not $INSTALL_PHAH) { $needRegister = $false }

if ($needRegister) {
    if (Test-Path $defaultCustom) {
        Copy-Item -Force $defaultCustom "$RIME_DIR\default.custom.yaml.bak"

        $content = Read-RimeText $defaultCustom
        if ($content -match '- schema:') {
            $lines = @(Get-RimeLines $defaultCustom)
            $lastIdx = -1
            for ($i = 0; $i -lt $lines.Count; $i++) {
                if ($lines[$i] -match '- schema:') { $lastIdx = $i }
            }
            if ($lastIdx -ge 0) {
                $indent = $lines[$lastIdx] -replace '- schema:.*', ''
                $newLine = "${indent}- schema: phah_taibun"
                $newLines = @($lines[0..$lastIdx] + $newLine + (Get-RimeTail -Lines $lines -AfterIndex $lastIdx))
                Write-RimeText -Path $defaultCustom -Text (($newLines -join "`n") + "`n")
            }
        } elseif ((Get-RimeLines $defaultCustom | Select-Object -First 1) -match '^__patch:') {
            Add-RimeText -Path $defaultCustom -Text "  - patch/+:`n      schema_list/@next:`n        schema: phah_taibun"
        } else {
            # 檔案可能是空的或只有註解：沒有 patch: 錨點就先補上，
            # 否則 @next 追加會落在結構外，產生無法解析的 YAML。
            if ($content -notmatch '(?m)^patch:\s*$') {
                Add-RimeText -Path $defaultCustom -Text "patch:"
            }
            Add-RimeText -Path $defaultCustom -Text "  schema_list/@next:`n    schema: phah_taibun"
        }
        Write-Host "  已將 phah_taibun 追加到 default.custom.yaml（保留既有方案，不會因此取代）" -ForegroundColor Green
    } else {
        # 安裝預設的 default.custom.yaml
        Copy-OrDownload -SourcePath "schema/default.custom.yaml" -DestinationPath $defaultCustom
        Write-Host "  default.custom.yaml（新建）" -ForegroundColor Green
    }
}

# ============================================================
# Step 2.55: 舊安裝補註冊 Telex 方案（既有 default.custom.yaml 已含
# phah_taibun，主註冊步驟會跳過，需另行追加）
# ============================================================
# default.custom.yaml 有兩種格式：__patch:（patch 列表）與 patch:（單一 map）。
# 直接把 schema_list/@next 1: 附加到檔尾會落在結構外，造成 YAML 解析失敗
# （所有方案註冊失效），必須依格式插入。
if ($INSTALL_PHAH -and (Test-Path $defaultCustom) -and -not (Select-String -Path $defaultCustom -Pattern "phah_taibun_telex" -Quiet)) {
    Copy-Item -Force $defaultCustom "$RIME_DIR\default.custom.yaml.bak"

    $content = Read-RimeText $defaultCustom
    if ($content -match '(?m)^\s*- schema: phah_taibun\s*$') {
        $lines = @(Get-RimeLines $defaultCustom)
        $lastIdx = -1
        for ($i = 0; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -match '^\s*- schema: phah_taibun\s*$') { $lastIdx = $i }
        }
        $indent = $lines[$lastIdx] -replace '- schema:.*', ''
        $newLine = "${indent}- schema: phah_taibun_telex"
        $newLines = @($lines[0..$lastIdx] + $newLine + (Get-RimeTail -Lines $lines -AfterIndex $lastIdx))
        Write-RimeText -Path $defaultCustom -Text (($newLines -join "`n") + "`n")
    } elseif ((Get-RimeLines $defaultCustom | Select-Object -First 1) -match '^__patch:') {
        Add-RimeText -Path $defaultCustom -Text "  - patch/+:`n      schema_list/@next 1:`n        schema: phah_taibun_telex"
    } else {
        Add-RimeText -Path $defaultCustom -Text "  schema_list/@next 1:`n    schema: phah_taibun_telex"
    }
    Write-Host "  已將 phah_taibun_telex 追加到 default.custom.yaml（保留既有方案，不會因此取代）" -ForegroundColor Green
}

# ============================================================
# Step 2.5: save_options — 記住 F4 選過的 TL/POJ、漢羅/全羅
# ============================================================
if ($INSTALL_PHAH -and (Test-Path $defaultCustom)) {
    if (-not (Select-String -Path $defaultCustom -Pattern "poj_mode" -Quiet)) {
        Copy-Item -Force $defaultCustom "$RIME_DIR\default.custom.yaml.bak"
        if ((Get-RimeLines $defaultCustom | Select-Object -First 1) -match '^__patch:') {
            Add-RimeText -Path $defaultCustom -Text "  - patch/+:`n      switcher/save_options/@before 0: poj_mode`n      switcher/save_options/@next: full_romanization"
        } else {
            $lines = @(Get-RimeLines $defaultCustom)
            $newLines = foreach ($line in $lines) {
                $line
                if ($line -match '^patch:') {
                    "  switcher/save_options/@before 0: poj_mode"
                    "  switcher/save_options/@next: full_romanization"
                }
            }
            Write-RimeText -Path $defaultCustom -Text (($newLines -join "`n") + "`n")
        }
        Write-Host "  已將 poj_mode / full_romanization 加入 save_options（記住模式選擇）" -ForegroundColor Green
    }
}

# ============================================================
# 確保 default.custom.yaml 存在（僅安裝嘸蝦米且全新環境時建立最小檔案）
# ============================================================
if (-not (Test-Path $defaultCustom)) {
    if ($INSTALL_PHAH) {
        Copy-OrDownload -SourcePath "schema/default.custom.yaml" -DestinationPath $defaultCustom
    } else {
        Write-RimeText -Path $defaultCustom -Text "patch:`n"
    }
    Write-Host "  default.custom.yaml（新建）" -ForegroundColor Green
}

# ============================================================
# Step 2.6: 詢問要保留哪些既有輸入法（原設定已於前面時間戳備份）
# ============================================================
if ($INTERACTIVE) {
    $currentSchemaIds = @(Get-RimeSchemaIds -Path $defaultCustom)

    if ($currentSchemaIds.Count -gt 0) {
        Write-Host "目前 default.custom.yaml 的方案清單："
        for ($i = 0; $i -lt $currentSchemaIds.Count; $i++) {
            Write-Host ("  {0}. {1}" -f ($i + 1), $currentSchemaIds[$i]) -ForegroundColor Cyan
        }
        $keepAnswer = Read-Host "要保留哪些？（Enter=全部保留，或輸入編號如 1,3）"
        if ($null -ne $keepAnswer -and $keepAnswer.Trim() -ne "") {
            $keepIds = @()
            foreach ($token in ($keepAnswer -split '[,，\s]+')) {
                if ($token -match '^\d+$') {
                    $idx = [int]$token - 1
                    if ($idx -ge 0 -and $idx -lt $currentSchemaIds.Count) { $keepIds += $currentSchemaIds[$idx] }
                }
            }
            # 剛安裝的方案不可被剪掉，否則會變成「裝了卻沒註冊」。
            $protectedIds = @()
            if ($INSTALL_PHAH) { $protectedIds += @("phah_taibun", "phah_taibun_telex") }
            if ($INSTALL_LIUR) { $protectedIds += "liur" }

            $dropIds = @($currentSchemaIds | Where-Object { $keepIds -notcontains $_ -and $protectedIds -notcontains $_ })
            if ($dropIds.Count -gt 0) {
                $origLines = @(Get-RimeLines $defaultCustom)
                $keptLines = New-Object System.Collections.Generic.List[string]
                for ($i = 0; $i -lt $origLines.Count; $i++) {
                    $line = $origLines[$i]
                    if ($line -match '^\s*- schema:\s*(\S+)\s*$') {
                        if ($dropIds -contains $Matches[1]) { continue }
                        $keptLines.Add($line)
                        continue
                    }
                    if ($line -match '^\s*schema_list/@next(\s+\d+)?:\s*$' -and
                            $i + 1 -lt $origLines.Count -and $origLines[$i + 1] -match '^\s+schema:\s*(\S+)\s*$') {
                        if ($dropIds -contains $Matches[1]) { $i++; continue }
                        $keptLines.Add($line)
                        $i++
                        $keptLines.Add($origLines[$i])
                        continue
                    }
                    $keptLines.Add($line)
                }
                Write-RimeText -Path $defaultCustom -Text (($keptLines -join "`n") + "`n")
                Write-Host "  已移除未選擇的方案：$($dropIds -join ', ')" -ForegroundColor Yellow
            } else {
                Write-Host "  保留全部既有方案" -ForegroundColor Green
            }
        } else {
            Write-Host "  保留全部既有方案" -ForegroundColor Green
        }
    }
}

# ============================================================
# Step 2.7: 保留注音輸入法（bopomofo）— 預設保留
# ============================================================
if ($INTERACTIVE -and -not (Select-String -Path $defaultCustom -Pattern "schema: bopomofo\s*$" -Quiet)) {
    $bopomofoAnswer = Read-Host "要保留注音輸入法（bopomofo）嗎？(Y/n)"
    if ($bopomofoAnswer -notmatch '^[nN]') {
        Add-SchemaEntry -SchemaId "bopomofo"
        Write-Host "  已將 bopomofo（注音）加入方案清單" -ForegroundColor Green
    }
}

# ============================================================
# Step 3: 安裝芫荽字體
# ============================================================
if ($INSTALL_PHAH) {
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
}

# ============================================================
# Step 3.5: 選裝嘸蝦米（rime-liur）— 下載公開 fork 的整份方案
# ============================================================
if ($INSTALL_LIUR) {
    Write-Host ""
    Write-Host "[ Step 3.5: 安裝嘸蝦米（rime-liur） ]" -ForegroundColor Green
    Write-Host ""

    if ($INTERACTIVE) {
        Write-Host "請選擇嘸蝦米版本：" -ForegroundColor Yellow
        Write-Host "  1. 完整版（中打含英文詞庫版）（推薦）"
        Write-Host "  2. 基礎版（中打不含英文詞庫）"
        $liurChoice = Read-Host "請輸入選項 (1 或 2，Enter=1)"
        if ($liurChoice -eq "2") { $LIUR_VERSION = "chinese-only" } else { $LIUR_VERSION = "mixed" }
    } else {
        $LIUR_VERSION = "mixed"
    }
    Write-Host ""

    try {
        Write-Host "正在從 GitHub 取得嘸蝦米檔案清單（$LIUR_REPO）..."
        $liurTree = Invoke-RestMethod -Uri $LIUR_API -Method Get
        if (-not $liurTree.tree) { throw "無法解析檔案清單" }

        $LIUR_EXCLUDE = @(
            "^docs/",
            "^README\.md$",
            "^LICENSE$",
            "^\.gitignore$",
            "^rime_liur_installer\.sh$",
            "^rime_liur_installer\.ps1$",
            "^rime_liur_installer_linux\.sh$"
        )
        # 使用者的自訂檔一律保留，不覆蓋（同嘸蝦米安裝腳本的「保留」選項）。
        $LIUR_CUSTOM_FILES = @("openxiami_CustomWord.dict.yaml", "default.custom.yaml", "weasel.custom.yaml")

        $liurRoot = @()
        $liurLua = @()
        $liurLunar = @()
        $liurOpencc = @()
        $liurConfigs = @()
        $liurFonts = @()
        $liurFontsWin = @()
        # 遠端檔案大小：本地已存在且大小相同就跳過，重灌不再全部重抓。
        $liurSizes = @{}
        foreach ($item in $liurTree.tree) {
            if ($item.type -ne "blob") { continue }
            $path = $item.path
            $excluded = $false
            foreach ($pattern in $LIUR_EXCLUDE) {
                if ($path -match $pattern) { $excluded = $true; break }
            }
            if ($excluded) { continue }

            $liurSizes[$path] = [long]$item.size
            if ($path -match "^lua/lunar_calendar/") { $liurLunar += $path }
            elseif ($path -match "^lua/") { $liurLua += $path }
            elseif ($path -match "^opencc/") { $liurOpencc += $path }
            elseif ($path -match "^configs/") { $liurConfigs += $path }
            elseif ($path -match "^fonts/Windows Only/") { $liurFontsWin += $path }
            elseif ($path -match "^fonts/") { $liurFonts += $path }
            elseif ($path -notmatch "/" -and $path -ne "rime.lua") { $liurRoot += $path }
        }

        $liurFileCount = $liurRoot.Count + $liurLua.Count + $liurLunar.Count + $liurOpencc.Count + $liurConfigs.Count + 1
        Write-Host "找到 $liurFileCount 個方案檔案、$($liurFonts.Count + $liurFontsWin.Count) 個字體"

        New-Item -ItemType Directory -Force -Path "$RIME_DIR\lua\lunar_calendar" | Out-Null
        New-Item -ItemType Directory -Force -Path "$RIME_DIR\opencc" | Out-Null
        New-Item -ItemType Directory -Force -Path "$RIME_DIR\configs" | Out-Null

        $liurCurrent = 0

        foreach ($file in $liurRoot) {
            $liurCurrent++
            if ($LIUR_CUSTOM_FILES -contains $file -and (Test-Path "$RIME_DIR\$file")) {
                Show-Progress -Current $liurCurrent -Total $liurFileCount -FileName "$file [保留]"
            } elseif ((Test-Path "$RIME_DIR\$file") -and $liurSizes.ContainsKey($file) -and
                    (Get-Item "$RIME_DIR\$file").Length -eq $liurSizes[$file]) {
                Show-Progress -Current $liurCurrent -Total $liurFileCount -FileName "$file [已安裝]"
            } else {
                Show-Progress -Current $liurCurrent -Total $liurFileCount -FileName $file
                Invoke-WebRequest -Uri "$LIUR_RAW/$file" -OutFile "$RIME_DIR\$file" | Out-Null
            }
        }

        foreach ($file in $liurLua) {
            $liurCurrent++
            $filename = Split-Path $file -Leaf
            if ((Test-Path "$RIME_DIR\lua\$filename") -and $liurSizes.ContainsKey($file) -and
                    (Get-Item "$RIME_DIR\lua\$filename").Length -eq $liurSizes[$file]) {
                Show-Progress -Current $liurCurrent -Total $liurFileCount -FileName "$filename [已安裝]"
            } else {
                Show-Progress -Current $liurCurrent -Total $liurFileCount -FileName $filename
                Invoke-WebRequest -Uri "$LIUR_RAW/$file" -OutFile "$RIME_DIR\lua\$filename" | Out-Null
            }
        }

        foreach ($file in $liurLunar) {
            $liurCurrent++
            $filename = Split-Path $file -Leaf
            if ((Test-Path "$RIME_DIR\lua\lunar_calendar\$filename") -and $liurSizes.ContainsKey($file) -and
                    (Get-Item "$RIME_DIR\lua\lunar_calendar\$filename").Length -eq $liurSizes[$file]) {
                Show-Progress -Current $liurCurrent -Total $liurFileCount -FileName "$filename [已安裝]"
            } else {
                Show-Progress -Current $liurCurrent -Total $liurFileCount -FileName $filename
                Invoke-WebRequest -Uri "$LIUR_RAW/$file" -OutFile "$RIME_DIR\lua\lunar_calendar\$filename" | Out-Null
            }
        }

        foreach ($file in $liurOpencc) {
            $liurCurrent++
            $filename = Split-Path $file -Leaf
            if ((Test-Path "$RIME_DIR\opencc\$filename") -and $liurSizes.ContainsKey($file) -and
                    (Get-Item "$RIME_DIR\opencc\$filename").Length -eq $liurSizes[$file]) {
                Show-Progress -Current $liurCurrent -Total $liurFileCount -FileName "$filename [已安裝]"
            } else {
                Show-Progress -Current $liurCurrent -Total $liurFileCount -FileName $filename
                Invoke-WebRequest -Uri "$LIUR_RAW/$file" -OutFile "$RIME_DIR\opencc\$filename" | Out-Null
            }
        }

        foreach ($file in $liurConfigs) {
            $liurCurrent++
            $filename = Split-Path $file -Leaf
            Show-Progress -Current $liurCurrent -Total $liurFileCount -FileName $filename
            Invoke-WebRequest -Uri "$LIUR_RAW/$file" -OutFile "$RIME_DIR\configs\$filename" | Out-Null
        }

        # rime.lua：嘸蝦米的 rime.lua 含完整函式定義，逐行比對會誤判（例如 end 這類短行），
        # 故以整份附加合併，並用註冊符號偵測避免重複追加。
        $liurCurrent++
        $rimeLuaDest = "$RIME_DIR\rime.lua"
        $liurRimeLua = Join-Path $env:TEMP "rime_liur_rime.lua"
        Invoke-WebRequest -Uri "$LIUR_RAW/rime.lua" -OutFile $liurRimeLua | Out-Null
        if (-not (Test-Path $rimeLuaDest)) {
            Show-Progress -Current $liurCurrent -Total $liurFileCount -FileName "rime.lua"
            Copy-Item -Force $liurRimeLua $rimeLuaDest
        } elseif (-not (Select-String -Path $rimeLuaDest -Pattern "liu_w2c_sorter" -Quiet)) {
            Show-Progress -Current $liurCurrent -Total $liurFileCount -FileName "rime.lua [合併]"
            Copy-Item -Force $rimeLuaDest "$RIME_DIR\rime.lua.bak"
            Add-RimeText -Path $rimeLuaDest -Text ((Read-RimeText $liurRimeLua).TrimEnd("`n"))
        } else {
            Show-Progress -Current $liurCurrent -Total $liurFileCount -FileName "rime.lua [已含嘸蝦米]"
        }
        Remove-Item -Force $liurRimeLua -ErrorAction SilentlyContinue

        Write-Host ""

        # 依版本配置 liur.schema.yaml（與嘸蝦米安裝腳本相同的兩種版本）
        if ($LIUR_VERSION -eq "mixed") {
            Copy-Item -Force "$RIME_DIR\configs\liur.schema.yaml" "$RIME_DIR\liur.schema.yaml"
            Write-Host "  已配置嘸蝦米完整版（中打含英文詞庫版）" -ForegroundColor Green
        } else {
            Copy-Item -Force "$RIME_DIR\configs\liur.chinese-only.schema.yaml" "$RIME_DIR\liur.schema.yaml"
            Write-Host "  已配置嘸蝦米基礎版（中打不含英文詞庫）" -ForegroundColor Green
        }
        Remove-Item -Recurse -Force "$RIME_DIR\configs" -ErrorAction SilentlyContinue

        # 註冊方案（只追加，不動既有清單）
        Add-SchemaEntry -SchemaId "liur"
        if ($LIUR_VERSION -eq "mixed") { Add-SchemaEntry -SchemaId "easy_en" }
        Write-Host "  已將 liur 加入 default.custom.yaml（保留既有方案）" -ForegroundColor Green

        # 字體（已安裝則跳過）
        $liurFontTotal = $liurFonts.Count + $liurFontsWin.Count
        if ($liurFontTotal -gt 0) { New-Item -ItemType Directory -Force -Path $FONT_DIR | Out-Null }
        $liurFontCurrent = 0
        foreach ($file in $liurFonts) {
            $liurFontCurrent++
            $filename = Split-Path $file -Leaf
            if (Test-Path "$FONT_DIR\$filename") {
                Show-Progress -Current $liurFontCurrent -Total $liurFontTotal -FileName "$filename [已安裝]"
            } else {
                Show-Progress -Current $liurFontCurrent -Total $liurFontTotal -FileName $filename
                Invoke-WebRequest -Uri "$LIUR_RAW/$file" -OutFile "$FONT_DIR\$filename" | Out-Null
            }
        }
        foreach ($file in $liurFontsWin) {
            $liurFontCurrent++
            $filename = Split-Path $file -Leaf
            if (Test-Path "$FONT_DIR\$filename") {
                Show-Progress -Current $liurFontCurrent -Total $liurFontTotal -FileName "$filename [已安裝]"
            } else {
                Show-Progress -Current $liurFontCurrent -Total $liurFontTotal -FileName $filename
                $encodedPath = $file -replace " ", "%20"
                Invoke-WebRequest -Uri "$LIUR_RAW/$encodedPath" -OutFile "$FONT_DIR\$filename" | Out-Null
            }
        }
        if ($liurFontTotal -gt 0) { Write-Host "" }
    } catch {
        Write-Host ""
        Write-Host "嘸蝦米安裝失敗：$($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "拍台文不受影響。可稍後重試，或手動參考 https://github.com/$LIUR_REPO" -ForegroundColor Yellow
    }
}

# ============================================================
# Step 3.9: 整理 default.custom.yaml（乾淨排版＋說明註解；
# 使用者自有設定原樣保留，__patch: 複合格式不動）
# ============================================================
Convert-RimeDefaultCustom -Path $defaultCustom

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
    Write-Host "或右鍵工作列小狼毫圖示 →「重新部署」。" -ForegroundColor Yellow
    if (-not $DOWNLOADED_PAYLOAD) {
        Write-Host "方案檔已寫入 Rime 資料夾，安裝程式不會因此失敗。" -ForegroundColor Yellow
    } else {
        exit 1
    }
} else {
    $deployProcess = Start-Process -FilePath $deployer -ArgumentList "/deploy" -Wait -PassThru
    $deployExit = $deployProcess.ExitCode
    if ($null -ne $deployExit -and $deployExit -ne 0) {
        Write-Host "部署失敗：WeaselDeployer.exe 結束碼為 $deployExit。" -ForegroundColor Red
        Write-Host "請修正上方錯誤後重試：`"$deployer`" /deploy" -ForegroundColor Yellow
        Write-Host "或右鍵工作列小狼毫圖示 →「重新部署」。" -ForegroundColor Yellow
        if (-not $DOWNLOADED_PAYLOAD) {
            Write-Host "方案檔已寫入 Rime 資料夾，安裝程式不會因此失敗。" -ForegroundColor Yellow
        } else {
            exit 1
        }
    } else {
        Write-Host "已重新部署小狼毫。" -ForegroundColor Green
    }
}

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
