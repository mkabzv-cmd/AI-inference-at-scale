#!/usr/bin/env bash
set -euo pipefail

lesson_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$lesson_root"
mkdir -p artifacts
set +e
python3 src/plan_sweep.py \
  --config configs/invalid-sweep.json \
  --available configs/available-modules.json \
  --output artifacts/invalid-plan.json \
  > artifacts/expected-plan-failure.txt 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'ERROR: invalid target and merge order were accepted\n' >&2
  exit 1
fi
grep -q 'target modules not found' artifacts/expected-plan-failure.txt
grep -q 'must reload a nonquantized base' artifacts/expected-plan-failure.txt
printf 'PASS: invalid module target and NF4 merge order failed closed\n'
