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
    if ($filtered.Count -eq 0) {
        # All entries were phah_taibun — remove the file entirely
        Remove-Item $rimeLuaPath -Force
        Write-Host "Removed: rime.lua (was phah_taibun only)"
    } else {
        Set-Content -Path $rimeLuaPath -Value $filtered -Encoding UTF8
        Write-Host "Cleaned phah_taibun entries from rime.lua"
    }
}

# Remove phah_taibun from default.custom.yaml
$defaultCustom = Join-Path $RimeUserDir "default.custom.yaml"
if (Test-Path $defaultCustom) {
    $lines = Get-Content $defaultCustom -Encoding UTF8
    $filtered = $lines | Where-Object { $_ -notmatch "phah_taibun" }
    # Check if any schema entries remain
    $hasSchemas = $filtered | Where-Object { $_ -match "- schema:" }
    if ($hasSchemas) {
        Set-Content -Path $defaultCustom -Value $filtered -Encoding UTF8
        Write-Host "Removed phah_taibun from default.custom.yaml"
    } else {
        Write-Host "Warning: removing phah_taibun would leave no schemas in default.custom.yaml"
        Write-Host "         Keeping the file unchanged. Please edit manually if needed."
    }
}

# Preserve user custom dictionaries:
#   phah_taibun.custom.dict.yaml
#   phah_taibun.phrase.dict.yaml
Write-Host "Note: User custom dictionaries preserved (if any)"
Write-Host "Pre-uninstall complete!"
