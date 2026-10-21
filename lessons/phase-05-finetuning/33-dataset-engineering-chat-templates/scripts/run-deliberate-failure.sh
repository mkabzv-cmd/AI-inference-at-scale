#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${ARTIFACT_DIR:-$lesson_dir/artifacts}"
failure_log="$artifact_dir/expected-failure.txt"

mkdir -p "$artifact_dir"

set +e
python3 "$lesson_dir/src/build_dataset.py" \
  --input "$lesson_dir/data/broken/duplicate-and-license.jsonl" \
  --config "$lesson_dir/configs/dataset.json" \
  --output-dir "$artifact_dir/broken-dataset" \
  >"$failure_log" 2>&1
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: broken provenance fixture was accepted\n' >&2
  exit 1
fi

if ! grep -Eq 'license|duplicate audit' "$failure_log"; then
  printf 'FAIL: failure did not identify license or duplicate evidence\n' >&2
  exit 1
fi

printf 'PASS: invalid license/duplicate fixture was rejected; see %s\n' \
  "$failure_log"
