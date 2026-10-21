#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
report_dir="$(mktemp -d "${TMPDIR:-/tmp}/oms-lesson-49.XXXXXX")"
trap 'rm -rf "$report_dir"' EXIT

python3 "$lesson_dir/src/verify_capstone.py" \
  --workspace "$lesson_dir/fixtures/passing" \
  --json-report "$report_dir/passing.json"

python3 - "$report_dir/passing.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert report["overall_status"] == "pass"
assert report["validation_mode"] == "fixture"
assert report["live_release_qualified"] is False
print("PASS: the synthetic fixture proves verifier mechanics, not a live release")
PY

for overlay in "$lesson_dir"/fixtures/failures/*.json; do
  name="$(basename "$overlay" .json)"
  report="$report_dir/$name.json"
  if python3 "$lesson_dir/src/verify_capstone.py" \
    --workspace "$lesson_dir/fixtures/passing" \
    --overlay "$overlay" \
    --json-report "$report" \
    >"$report_dir/$name.out"; then
    echo "FAIL: deliberate failure unexpectedly passed: $name" >&2
    exit 1
  fi
  python3 - "$overlay" "$report" <<'PY'
import json
import sys
from pathlib import Path

overlay = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
report = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
observed = {item["code"] for item in report["violations"]}
missing = sorted(set(overlay["expect_codes"]) - observed)
if missing:
    raise SystemExit(f"expected violation codes not observed: {missing}")
print(f"PASS: rejected {overlay['name']} with expected codes={overlay['expect_codes']}")
PY
done

if python3 "$lesson_dir/src/verify_capstone.py" \
  --workspace "$lesson_dir/fixtures/passing" \
  --require-operator-run \
  --json-report "$report_dir/operator-required.json" \
  >"$report_dir/operator-required.out"; then
  echo "FAIL: a synthetic fixture qualified as an operator run" >&2
  exit 1
fi

python3 - "$report_dir/operator-required.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
codes = {item["code"] for item in report["violations"]}
assert "OPERATOR_RUN_REQUIRED" in codes
assert report["live_release_qualified"] is False
print("PASS: completion mode rejects synthetic evidence")
PY

workspace="$report_dir/new-workspace"
"$lesson_dir/scripts/init-workspace.sh" "$workspace"
if "$lesson_dir/scripts/init-workspace.sh" "$workspace"; then
  echo "FAIL: initializer overwrote a non-empty workspace" >&2
  exit 1
fi
if python3 "$lesson_dir/src/verify_capstone.py" \
  --workspace "$workspace" \
  --json-report "$report_dir/starter.json" \
  >"$report_dir/starter.out"; then
  echo "FAIL: unresolved starter workspace unexpectedly passed" >&2
  exit 1
fi
python3 - "$report_dir/starter.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
codes = {item["code"] for item in report["violations"]}
assert "UNRESOLVED_MARKER" in codes
assert report["live_release_qualified"] is False
PY
echo "PASS: initializer is no-overwrite and starter evidence fails closed"
echo "PASS: lesson-49 local fixture suite completed"
