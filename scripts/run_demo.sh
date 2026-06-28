#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Validating sample JSON contracts..."
python scripts/validate_json.py

echo
echo "Ensuring data directories exist..."
bash scripts/bootstrap_data_dirs.sh

echo
echo "Running sample pipeline through Timeline Planner (stage 6)..."
python -m integration.run_pipeline --use-sample-data --from-stage 1 --to-stage 6 --skip-ui --overwrite

echo
echo "Validating runtime JSON contracts..."
python scripts/validate_json.py --input-dir data/intermediate

echo
echo "Demo complete: data/intermediate/timeline.json"
