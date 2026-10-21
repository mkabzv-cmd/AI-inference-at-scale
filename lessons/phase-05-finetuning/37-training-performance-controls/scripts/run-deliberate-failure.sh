#!/usr/bin/env bash
set -euo pipefail

lesson_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$lesson_root"
mkdir -p artifacts
set +e
python3 src/detect_confounds.py \
  --input fixtures/confounded-results.json \
  > artifacts/expected-confound-failure.txt 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'ERROR: confounded performance comparison was accepted\n' >&2
  exit 1
fi
grep -q 'dataset_manifest_sha256' artifacts/expected-confound-failure.txt
grep -q 'maximum_optimizer_steps' artifacts/expected-confound-failure.txt
grep -q 'token_slots_per_optimizer_step' artifacts/expected-confound-failure.txt
printf 'PASS: changed data, run length, and token budget were detected\n'
