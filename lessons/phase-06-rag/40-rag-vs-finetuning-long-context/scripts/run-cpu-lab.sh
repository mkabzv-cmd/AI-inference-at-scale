#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${ARTIFACT_DIR:-$lesson_dir/artifacts}"
mkdir -p "$artifact_dir"

python3 "$lesson_dir/src/decision_matrix.py" \
  --strategies "$lesson_dir/configs/strategies.json" \
  --scenarios "$lesson_dir/configs/scenarios.json" \
  --output "$artifact_dir/decisions.json"

python3 "$lesson_dir/scripts/verify.py" \
  --results "$artifact_dir/decisions.json"

printf 'Decision evidence written under %s\n' "$artifact_dir"
