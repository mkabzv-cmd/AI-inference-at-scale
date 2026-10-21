#!/usr/bin/env bash
set -euo pipefail

: "${MODEL_BASE_URL:?Set the private port-forwarded endpoint URL}"
: "${MODEL_ID:?Set the exact served model or adapter name}"
lesson_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
evaluation_root="$lesson_root/../34-evaluation-before-optimization"
label="${1:?Pass base or tuned as the evidence label}"
case "$label" in base|tuned) ;; *) printf 'label must be base or tuned\n' >&2; exit 1 ;; esac
export ARTIFACT_DIR="$lesson_root/artifacts/evaluation-$label"
"$evaluation_root/scripts/run-endpoint-evaluation.sh"
if [[ "$label" == "tuned" ]]; then
  python3 "$evaluation_root/src/apply_gates.py" \
    --results "$ARTIFACT_DIR/endpoint-results.json" \
    --gates "$evaluation_root/configs/release-gates.json" \
    --output "$ARTIFACT_DIR/required-pass-decision.json" \
    --require-pass
fi
