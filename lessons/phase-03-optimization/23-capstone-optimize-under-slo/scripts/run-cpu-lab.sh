#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts
python3 src/select_candidate.py \
  --slo configs/slo.json \
  --results fixtures/candidate-results.synthetic.json \
  --output artifacts/results.json
python3 scripts/verify-results.py artifacts/results.json
