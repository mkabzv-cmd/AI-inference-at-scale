#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts
python3 src/memory_accounting.py \
  --model configs/model.json \
  --workloads configs/workloads.json \
  --vram-gib "${VRAM_GIB:-24}" \
  --utilization "${GPU_MEMORY_UTILIZATION:-0.80}" \
  --block-size "${KV_BLOCK_SIZE:-16}" \
  --output artifacts/results.json

python3 src/phase_simulator.py \
  --prompt-tokens 512 \
  --output-tokens 8 \
  --layers 24 \
  --hidden-size 896 \
  --output artifacts/prefill-decode-timeline.json

python3 scripts/verify-results.py artifacts/results.json
