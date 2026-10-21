#!/usr/bin/env bash
set -euo pipefail

lesson_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$lesson_root"

rm -rf -- artifacts/full artifacts/resumed
rm -f -- artifacts/resource-plan.json
mkdir -p artifacts/full artifacts/resumed

python3 src/lifecycle_simulator.py \
  --config configs/lifecycle.json \
  --output artifacts/full

python3 src/lifecycle_simulator.py \
  --config configs/lifecycle.json \
  --output artifacts/resumed \
  --stop-after 5

python3 src/lifecycle_simulator.py \
  --config configs/lifecycle.json \
  --output artifacts/resumed \
  --resume artifacts/resumed/checkpoint-0005.json

python3 src/verify_lifecycle.py \
  --full artifacts/full \
  --resumed artifacts/resumed

python3 src/resource_plan.py > artifacts/resource-plan.json
python3 -m json.tool artifacts/resource-plan.json >/dev/null
printf 'Evidence written to %s/artifacts\n' "$lesson_root"
