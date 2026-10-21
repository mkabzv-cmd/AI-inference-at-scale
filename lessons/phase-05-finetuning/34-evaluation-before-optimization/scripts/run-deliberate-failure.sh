#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${ARTIFACT_DIR:-$lesson_dir/artifacts}"
mutated="$artifact_dir/mutated-acceptance.jsonl"
failure_log="$artifact_dir/expected-lock-failure.txt"

mkdir -p "$artifact_dir"
cp "$lesson_dir/data/acceptance.jsonl" "$mutated"
printf '\n' >>"$mutated"

set +e
python3 "$lesson_dir/src/verify_lock.py" \
  --lock "$lesson_dir/acceptance.lock.json" \
  --acceptance "$mutated" \
  --config "$lesson_dir/configs/evaluation.json" \
  --evaluator "$lesson_dir/src/evaluate.py" \
  >"$failure_log" 2>&1
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: mutated acceptance set matched the frozen lock\n' >&2
  exit 1
fi
if ! grep -q 'acceptance_sha256 differs' "$failure_log"; then
  printf 'FAIL: lock verifier failed for an unexpected reason\n' >&2
  exit 1
fi
printf 'PASS: acceptance mutation was rejected; see %s\n' "$failure_log"
