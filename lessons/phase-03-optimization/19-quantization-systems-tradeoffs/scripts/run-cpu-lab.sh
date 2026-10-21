#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts
python3 src/quantization_lab.py \
  --matrix configs/experiment-matrix.json \
  --output artifacts/results.json
python3 scripts/verify-results.py \
  artifacts/results.json \
  configs/quality-gate.json
