#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TARGETS=(
  "data/intermediate"
  "data/final"
)

if [[ "${1:-}" != "--yes" ]]; then
  echo "Dry run. The following generated output directories would be removed:"
  printf '  %s\n' "${TARGETS[@]}"
  echo
  echo "Run scripts/clean_outputs.sh --yes to remove them."
  exit 0
fi

for target in "${TARGETS[@]}"; do
  if [[ -d "$target" ]]; then
    rm -rf -- "$target"
    echo "Removed $target"
  else
    echo "Skipped $target (not found)"
  fi
done
