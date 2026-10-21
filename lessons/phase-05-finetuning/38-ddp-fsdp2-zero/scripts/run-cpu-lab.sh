#!/usr/bin/env bash
set -euo pipefail

lesson_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$lesson_root"
rm -f -- artifacts/collectives.json artifacts/strategy-plan.json
mkdir -p artifacts
python3 src/collective_simulator.py --output artifacts/collectives.json
python3 src/strategy_planner.py \
  --config configs/strategy-study.json \
  --output artifacts/strategy-plan.json
python3 -m json.tool artifacts/collectives.json >/dev/null
python3 -m json.tool artifacts/strategy-plan.json >/dev/null
printf 'PASS: distributed correctness and memory arithmetic evidence written\n'
