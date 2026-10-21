#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts
python3 scripts/verify_study.py artifacts/raw
python3 scripts/compare.py artifacts/raw \
  --json-output artifacts/comparison.json \
  --markdown-output artifacts/report.md
test -f artifacts/decision.md || cp adr-template.md artifacts/decision.md
grep -q '^# Controlled engine comparison' artifacts/report.md
printf 'report built; complete artifacts/decision.md using evidence\n'
