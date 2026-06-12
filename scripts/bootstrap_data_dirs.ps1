$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

$dirs = @(
    "data/raw",
    "data/normalized",
    "data/keyframes",
    "data/intermediate",
    "data/final"
)

foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    New-Item -ItemType File -Force -Path (Join-Path $dir ".gitkeep") | Out-Null
    Write-Host "Ready: $dir"
}
