#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts
python3 src/reuse_lookahead_lab.py \
  --prefix configs/prefix-workload.json \
  --chunking configs/chunking-cases.json \
  --speculation configs/speculation-cases.json \
  --output artifacts/results.json
python3 scripts/verify-results.py artifacts/results.json
