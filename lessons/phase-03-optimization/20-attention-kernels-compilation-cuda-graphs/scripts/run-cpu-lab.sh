#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts
python3 src/attention_reference.py \
  --query-tokens 8 \
  --kv-tokens 11 \
  --head-dim 4 \
  --tile-k 3 \
  --output artifacts/attention-correctness.json
python3 src/mechanism_report.py \
  --shapes configs/shapes.json \
  --trace fixtures/eager.synthetic.json \
  --trace fixtures/fused.synthetic.json \
  --trace fixtures/cuda-graph.synthetic.json \
  --output artifacts/results.json
python3 scripts/verify-results.py
