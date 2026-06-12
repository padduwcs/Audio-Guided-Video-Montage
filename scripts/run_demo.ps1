$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

Write-Host "Validating sample JSON contracts..."
python scripts/validate_json.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Pipeline execution is not implemented yet."
Write-Host "Expected future flow:"
Write-Host "  Input Processor -> Audio Analyzer + Video Analyzer -> Embedding Indexer"
Write-Host "  -> Matching Engine -> Timeline Planner -> Review UI -> Renderer"
