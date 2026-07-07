param(
    [switch]$Yes
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

$targets = @(
    "data/intermediate",
    "data/normalized",
    "data/keyframes",
    "data/final"
)

if (-not $Yes) {
    Write-Host "Dry run. The following generated output directories would be removed:"
    foreach ($target in $targets) {
        Write-Host "  $target"
    }
    Write-Host ""
    Write-Host "Run .\scripts\clean_outputs.ps1 -Yes to remove them."
    exit 0
}

foreach ($target in $targets) {
    if (Test-Path $target) {
        New-Item -ItemType Directory -Force -Path $target | Out-Null
        Get-ChildItem -LiteralPath $target -Force |
            Where-Object { $_.Name -ne ".gitkeep" } |
            Remove-Item -Recurse -Force
        New-Item -ItemType File -Force -Path (Join-Path $target ".gitkeep") | Out-Null
        Write-Host "Cleaned $target (kept .gitkeep)"
    } else {
        New-Item -ItemType Directory -Force -Path $target | Out-Null
        New-Item -ItemType File -Force -Path (Join-Path $target ".gitkeep") | Out-Null
        Write-Host "Created $target with .gitkeep"
    }
}
