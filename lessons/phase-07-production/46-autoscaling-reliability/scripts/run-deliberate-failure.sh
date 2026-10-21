#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${ARTIFACT_DIR:-$lesson_dir/artifacts}"
study="$artifact_dir/unstable-study.json"
failure_log="$artifact_dir/expected-stability-failure.txt"
mkdir -p "$artifact_dir"

python3 "$lesson_dir/src/autoscaling_simulator.py" \
  --config "$lesson_dir/configs/unstable-simulation.json" \
  --strategies queue \
  --output "$study"

set +e
python3 "$lesson_dir/scripts/verify_stability.py" \
  --study "$study" \
  >"$failure_log" 2>&1
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: unstable autoscaling policy passed the action budget\n' >&2
  exit 1
fi
if ! grep -q 'scale action budget' "$failure_log"; then
  printf 'FAIL: stability verifier failed for an unexpected reason\n' >&2
  exit 1
fi
printf 'PASS: oscillating policy was rejected; see %s\n' "$failure_log"
