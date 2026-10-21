#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts
python3 src/validate_study.py fixtures/study-spec.json
python3 src/summarize_study.py \
  --spec fixtures/study-spec.json \
  --runs fixtures/runs.json \
  --cost fixtures/cost.json \
  --output artifacts/offline-summary.json \
  --report artifacts/offline-summary.md
python3 src/timeline_report.py \
  --input fixtures/failure.ndjson \
  --output artifacts/offline-failure-timeline.md
python3 src/cost_report.py \
  --start '2026-10-21T00:00:00Z' \
  --end '2026-10-21T01:00:00Z' \
  --nodes 3 \
  --gpus-per-node 1 \
  --price-per-node-hour 1 \
  --currency USD \
  --output artifacts/offline-cost.json
python3 - <<'PY'
import json
from pathlib import Path

summary = json.loads(Path("artifacts/offline-summary.json").read_text())
cost = json.loads(Path("artifacts/offline-cost.json").read_text())
assert summary["correctness"]["passed"] is True
assert summary["measurements"]["repetitions_per_strategy"] == 2
assert cost["gpu_hours"] == 3
assert cost["estimated_node_cost"] == 3
print("offline capstone pipeline: PASS")
PY

python3 - <<'PY'
import json
from pathlib import Path

source = Path("fixtures/runs.json")
runs = json.loads(source.read_text())
for run in runs:
    run["environment"]["model_revision"] = "d" * 40
Path("artifacts/consistent-but-unfrozen-runs.json").write_text(
    json.dumps(runs, indent=2) + "\n"
)
PY
set +e
python3 src/summarize_study.py \
  --spec fixtures/study-spec.json \
  --runs artifacts/consistent-but-unfrozen-runs.json \
  --output artifacts/rejected-summary.json \
  --report artifacts/rejected-summary.md >/dev/null
status=$?
set -e
if [[ "$status" -ne 1 ]]; then
  printf 'expected consistently wrong frozen input to exit 1, got %s\n' \
    "$status" >&2
  exit 1
fi
printf 'consistently wrong frozen input: correctly rejected\n'
