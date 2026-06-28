$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

Write-Host "Validating sample JSON contracts..."
python scripts/validate_json.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Ensuring data directories exist..."
& "$PSScriptRoot\bootstrap_data_dirs.ps1"

Write-Host ""
Write-Host "Running sample pipeline through Timeline Planner (stage 6)..."
python -m integration.run_pipeline --use-sample-data --from-stage 1 --to-stage 6 --skip-ui --overwrite
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Validating runtime JSON contracts..."
python scripts/validate_json.py --input-dir data/intermediate
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Demo complete: data/intermediate/timeline.json"
