#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DIRS=(
  "data/raw"
  "data/normalized"
  "data/keyframes"
  "data/intermediate"
  "data/final"
)

for dir in "${DIRS[@]}"; do
  mkdir -p "$dir"
  touch "$dir/.gitkeep"
  echo "Ready: $dir"
done
