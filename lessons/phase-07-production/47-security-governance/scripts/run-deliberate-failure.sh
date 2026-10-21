#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${ARTIFACT_DIR:-$lesson_dir/artifacts}"
bundle_dir="$artifact_dir/bundle"
failure_log="$artifact_dir/expected-tamper-failure.txt"

if [[ ! -f "$bundle_dir/provenance.json" ]]; then
  "$lesson_dir/scripts/run-cpu-lab.sh"
fi

printf 'tampered\n' >>"$bundle_dir/model-card.json"
set +e
python3 "$lesson_dir/src/verify_provenance.py" \
  --config "$lesson_dir/configs/bundle.json" \
  --provenance "$bundle_dir/provenance.json" \
  --bundle-dir "$bundle_dir" \
  >"$failure_log" 2>&1
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: modified model card passed provenance verification\n' >&2
  exit 1
fi
if ! grep -q 'sha256 mismatch' "$failure_log"; then
  printf 'FAIL: provenance check failed for an unexpected reason\n' >&2
  exit 1
fi

set +e
python3 "$lesson_dir/scripts/verify-k8s-security.py" \
  --manifest "$lesson_dir/k8s/broken-workload.yaml" \
  >"$artifact_dir/expected-policy-failure.txt" 2>&1
policy_status=$?
set -e
if [[ "$policy_status" -eq 0 ]]; then
  printf 'FAIL: unsafe Kubernetes fixture passed policy verification\n' >&2
  exit 1
fi

printf 'PASS: tampered artifact and unsafe workload were rejected\n'
