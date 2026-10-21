#!/usr/bin/env bash
set -euo pipefail
mkdir -p artifacts
python3 src/compare_results.py \
  --dp fixtures/dp.json \
  --tp fixtures/tp.json \
  --pp fixtures/pp.json \
  --output artifacts/fixture-comparison.json \
  --report artifacts/fixture-comparison.md
set +e
python3 src/check_tp_shape.py \
  --config inputs/incompatible-config.json \
  --tp 3 \
  --output artifacts/incompatible-tp.json >/dev/null
status=$?
set -e
if [[ "$status" -ne 2 ]]; then
  printf 'expected incompatible TP fixture to exit 2, got %s\n' "$status" >&2
  exit 1
fi
printf 'comparison fixture and incompatible-shape failure: PASS\n'
