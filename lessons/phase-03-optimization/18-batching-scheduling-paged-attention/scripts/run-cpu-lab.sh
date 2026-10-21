#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts
python3 src/scheduler_sim.py \
  --workload configs/workload.json \
  --matrix configs/experiment-matrix.json \
  --output artifacts/results.json
python3 src/render_timeline.py artifacts/results.json \
  > artifacts/scheduler-timeline.md
python3 scripts/verify-results.py artifacts/results.json
echo "timeline: artifacts/scheduler-timeline.md"
