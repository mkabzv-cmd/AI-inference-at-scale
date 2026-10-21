#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${ARTIFACT_DIR:-$lesson_dir/artifacts}"
state_dir="$artifact_dir/environments"
good="$lesson_dir/releases/candidate-good.json"
invalid="$lesson_dir/releases/candidate-invalid.json"

rm -rf -- "$artifact_dir"
mkdir -p "$artifact_dir"

python3 "$lesson_dir/src/validate_release.py" --release "$good"
python3 "$lesson_dir/src/render_release.py" \
  --release "$good" \
  --template "$lesson_dir/gitops/deployment.yaml.tpl" \
  --namespace oms-lesson-48-staging \
  --output "$artifact_dir/rendered-staging.yaml"

python3 "$lesson_dir/src/promote.py" \
  --candidate "$good" \
  --environment staging \
  --state-dir "$state_dir" \
  --expected-current NONE

"$lesson_dir/scripts/run-smoke.sh" "$state_dir/staging.json"

python3 "$lesson_dir/src/promote.py" \
  --candidate "$good" \
  --environment production \
  --state-dir "$state_dir" \
  --expected-current NONE

set +e
python3 "$lesson_dir/src/validate_release.py" \
  --release "$invalid" \
  >"$artifact_dir/expected-invalid-release.txt" 2>&1
invalid_status=$?
set -e
if [[ "$invalid_status" -eq 0 ]]; then
  printf 'FAIL: invalid release passed the metadata gates\n' >&2
  exit 1
fi

python3 "$lesson_dir/scripts/verify_pipeline.py" \
  --state-dir "$state_dir" \
  --expected-release oms-2026-10-21.1

printf 'Pipeline evidence written under %s\n' "$artifact_dir"
