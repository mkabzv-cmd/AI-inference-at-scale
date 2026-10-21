#!/usr/bin/env bash
set -euo pipefail

lesson_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$lesson_root"
mkdir -p artifacts
torchrun --standalone --nnodes=1 --nproc-per-node=3 \
  src/ddp_equivalence.py \
  --backend gloo \
  --output artifacts/torch-ddp-equivalence.json
python3 -m json.tool artifacts/torch-ddp-equivalence.json >/dev/null
