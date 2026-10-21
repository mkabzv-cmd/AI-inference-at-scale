#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${ARTIFACT_DIR:-$lesson_dir/artifacts}"
broken="$artifact_dir/broken-requests.ndjson"
failure_log="$artifact_dir/expected-correlation-failure.txt"

if [[ ! -f "$artifact_dir/requests.ndjson" ]]; then
  printf 'Run ./scripts/run-local-lab.sh first\n' >&2
  exit 1
fi

cp "$artifact_dir/requests.ndjson" "$broken"
python3 - "$broken" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
rows = [json.loads(line) for line in path.read_text().splitlines() if line]
rows[0]["request_id"] = "correlation-was-destroyed"
path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n")
PY

set +e
python3 "$lesson_dir/scripts/verify.py" \
  --records "$broken" \
  --server-log "$artifact_dir/server.ndjson" \
  --report "$artifact_dir/capacity-report.json" \
  >"$failure_log" 2>&1
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  printf 'FAIL: destroyed request correlation was accepted\n' >&2
  exit 1
fi
if ! grep -q 'do not correlate exactly' "$failure_log"; then
  printf 'FAIL: verifier failed for an unexpected reason\n' >&2
  exit 1
fi
printf 'PASS: broken correlation was rejected; see %s\n' "$failure_log"
