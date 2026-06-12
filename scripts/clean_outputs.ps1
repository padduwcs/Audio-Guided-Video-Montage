param(
    [switch]$Yes
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

$targets = @(
    "data/intermediate",
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
        Remove-Item -Recurse -Force $target
        New-Item -ItemType Directory -Force -Path $target | Out-Null
        New-Item -ItemType File -Force -Path (Join-Path $target ".gitkeep") | Out-Null
        Write-Host "Removed $target (recreated with .gitkeep)"
    } else {
        Write-Host "Skipped $target (not found)"
    }
}
