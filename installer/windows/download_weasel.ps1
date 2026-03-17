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
