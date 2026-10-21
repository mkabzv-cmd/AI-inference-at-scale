#!/usr/bin/env bash
set -euo pipefail

lesson_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$lesson_root"
if ! python3 -c 'import torch' >/dev/null 2>&1; then
  printf '%s\n' \
    'PyTorch is required for this optional probe; install the Phase-5 pinned environment first.' >&2
  exit 1
fi
mkdir -p artifacts/dataloader
python3 src/dataloader_probe.py \
  --workers 0 \
  --output artifacts/dataloader/workers-0.json
python3 src/dataloader_probe.py \
  --workers 2 \
  --output artifacts/dataloader/workers-2.json
printf 'Repeat both treatments; do not infer model throughput from this probe.\n'
