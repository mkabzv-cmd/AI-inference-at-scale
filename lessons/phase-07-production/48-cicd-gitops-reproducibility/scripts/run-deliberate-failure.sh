#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${ARTIFACT_DIR:-$lesson_dir/artifacts}"
state_dir="$artifact_dir/environments"
good="$lesson_dir/releases/candidate-good.json"
regression="$lesson_dir/releases/candidate-regression.json"

if [[ ! -f "$state_dir/production.json" ]]; then
  "$lesson_dir/scripts/run-local-pipeline.sh"
fi

python3 "$lesson_dir/src/validate_release.py" --release "$regression"
python3 "$lesson_dir/src/promote.py" \
  --candidate "$regression" \
  --environment staging \
  --state-dir "$state_dir" \
  --expected-current oms-2026-10-21.1

set +e
"$lesson_dir/scripts/run-smoke.sh" "$state_dir/staging.json" \
  >"$artifact_dir/expected-smoke-failure.txt" 2>&1
smoke_status=$?
set -e
if [[ "$smoke_status" -eq 0 ]]; then
  printf 'FAIL: regression passed the behavioral smoke gate\n' >&2
  exit 1
fi

production_id="$(
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["release_id"])' \
    "$state_dir/production.json"
)"
if [[ "$production_id" != "oms-2026-10-21.1" ]]; then
  printf 'FAIL: production changed despite failed staging smoke\n' >&2
  exit 1
fi

python3 "$lesson_dir/src/promote.py" \
  --candidate "$good" \
  --environment staging \
  --state-dir "$state_dir" \
  --expected-current oms-2026-10-21.2-regression

python3 "$lesson_dir/scripts/verify_pipeline.py" \
  --state-dir "$state_dir" \
  --expected-release oms-2026-10-21.1

printf 'PASS: regression was contained in staging and staging rolled back\n'
