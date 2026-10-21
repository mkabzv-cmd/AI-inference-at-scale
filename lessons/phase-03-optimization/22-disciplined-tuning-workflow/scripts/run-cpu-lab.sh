#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts
python3 src/diagnose.py \
  --case cases/queue-bound.json \
  --case cases/kv-bound.json \
  --case cases/client-bound.json \
  --baseline cases/baseline-run.json \
  --candidate cases/misleading-fast-run.json \
  --gate configs/quality-slo-gate.json \
  --output artifacts/results.json
python3 scripts/verify-results.py artifacts/results.json
