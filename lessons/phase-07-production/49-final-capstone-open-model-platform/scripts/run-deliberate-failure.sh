#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
overlay="${1:-$lesson_dir/fixtures/failures/public-exposure.json}"

if [[ ! -f "$overlay" ]]; then
  echo "failure overlay does not exist: $overlay" >&2
  exit 2
fi

report="$(mktemp "${TMPDIR:-/tmp}/oms-lesson-49-failure.XXXXXX.json")"
trap 'rm -f "$report"' EXIT
if python3 "$lesson_dir/src/verify_capstone.py" \
  --workspace "$lesson_dir/fixtures/passing" \
  --overlay "$overlay" \
  --json-report "$report" \
  --replace-report; then
  echo "FAIL: deliberate failure unexpectedly passed" >&2
  exit 1
fi
python3 - "$report" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print("expected-rejection-codes=" + ",".join(
    sorted({item["code"] for item in report["violations"]})
))
PY
echo "PASS: verifier rejected the deliberate failure without changing the fixture"
