#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TARGETS=(
  "data/intermediate"
  "data/normalized"
  "data/keyframes"
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
    mkdir -p "$target"
    find "$target" -mindepth 1 ! -name ".gitkeep" -exec rm -rf {} +
    touch "$target/.gitkeep"
    echo "Cleaned $target (kept .gitkeep)"
  else
    mkdir -p "$target"
    touch "$target/.gitkeep"
    echo "Created $target with .gitkeep"
  fi
done
