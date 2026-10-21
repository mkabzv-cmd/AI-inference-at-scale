#!/usr/bin/env bash
set -euo pipefail

lesson_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$lesson_root"
rm -f -- artifacts/lora-math.json artifacts/sweep-plan.json
mkdir -p artifacts

python3 src/lora_math.py --output artifacts/lora-math.json
python3 src/plan_sweep.py \
  --config configs/sweep.json \
  --available configs/available-modules.json \
  --output artifacts/sweep-plan.json
python3 -m json.tool artifacts/lora-math.json >/dev/null
python3 -m json.tool artifacts/sweep-plan.json >/dev/null
printf 'PASS: LoRA math and candidate arithmetic evidence written\n'
