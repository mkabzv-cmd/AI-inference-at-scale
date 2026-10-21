#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts/fixture-logs
cp fixtures/sample-rank0.txt artifacts/fixture-logs/rank-0.log
python3 src/analyze_results.py \
  --logs artifacts/fixture-logs \
  --output artifacts/fixture-results.json \
  --report artifacts/fixture-report.md \
  --fixture
python3 - <<'PY'
import json
from pathlib import Path

d = json.loads(Path("artifacts/fixture-results.json").read_text())
assert d["correctness"]["passed"] is True
assert d["environment"]["fixture"] is True
assert len(d["measurements"]["records"]) == 3
print("fixture analyzer: PASS")
PY

mkdir -p artifacts/partial-logs
grep '"operation":"ping-pong"' fixtures/sample-rank0.txt \
  >artifacts/partial-logs/rank-0.log
set +e
python3 src/analyze_results.py \
  --logs artifacts/partial-logs \
  --output artifacts/partial-results.json \
  --report artifacts/partial-report.md \
  --fixture >/dev/null
status=$?
set -e
if [[ "$status" -ne 1 ]]; then
  printf 'expected incomplete operation set to exit 1, got %s\n' "$status" >&2
  exit 1
fi
printf 'incomplete operation set: correctly rejected\n'
