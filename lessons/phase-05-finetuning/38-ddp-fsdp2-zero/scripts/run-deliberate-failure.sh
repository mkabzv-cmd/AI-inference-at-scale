#!/usr/bin/env bash
set -euo pipefail

lesson_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$lesson_root"
mkdir -p artifacts
set +e
python3 src/uneven_batch_failure.py \
  --output artifacts/uneven-batches.json \
  > artifacts/expected-uneven-failure.txt 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'ERROR: uneven rank batches unexpectedly passed equivalence\n' >&2
  exit 1
fi
grep -q 'unweighted rank mean is not the global sample mean' \
  artifacts/expected-uneven-failure.txt
python3 -m json.tool artifacts/uneven-batches.json >/dev/null
printf 'PASS: uneven local-batch bias is measured and rejected\n'
