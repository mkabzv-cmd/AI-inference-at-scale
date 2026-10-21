#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${ARTIFACT_DIR:-$lesson_dir/artifacts}"
mkdir -p "$artifact_dir"

python3 "$lesson_dir/src/autoscaling_simulator.py" \
  --config "$lesson_dir/configs/simulation.json" \
  --output "$artifact_dir/scaling-study.json"

python3 "$lesson_dir/scripts/verify.py" \
  --study "$artifact_dir/scaling-study.json"

printf 'Scaling evidence written under %s\n' "$artifact_dir"
