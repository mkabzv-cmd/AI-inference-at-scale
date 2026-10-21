#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${ARTIFACT_DIR:-$lesson_dir/artifacts}"
failure_log="$artifact_dir/expected-failure.txt"
mkdir -p "$artifact_dir"

set +e
python3 "$lesson_dir/src/decision_matrix.py" \
  --strategies "$lesson_dir/configs/strategies.json" \
  --scenarios "$lesson_dir/configs/broken-scenario.json" \
  --output "$artifact_dir/should-not-exist.json" \
  >"$failure_log" 2>&1
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: an unknown decision criterion was accepted\n' >&2
  exit 1
fi
if ! grep -q 'unknown criteria' "$failure_log"; then
  printf 'FAIL: decision matrix failed for an unexpected reason\n' >&2
  exit 1
fi
printf 'PASS: unknown criterion was rejected; see %s\n' "$failure_log"
