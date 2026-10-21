#!/usr/bin/env bash
set -euo pipefail

operation="${1:-all-reduce}"
elements="${2:-1024}"
mkdir -p artifacts/local

command -v torchrun >/dev/null 2>&1 || {
  printf 'torchrun not found; activate the lesson virtual environment\n' >&2
  exit 2
}

torchrun --standalone --nproc-per-node=3 \
  src/collectives_lab.py \
  --backend gloo \
  --operation "$operation" \
  --elements "$elements" \
  --expect-world-size 3 \
  --output-dir artifacts/local

./scripts/verify-local.py artifacts/local/summary.json
