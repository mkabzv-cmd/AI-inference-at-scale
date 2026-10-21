#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${ARTIFACT_DIR:-$lesson_dir/artifacts}"

: "${MODEL_BASE_URL:?Set MODEL_BASE_URL, for example http://127.0.0.1:8000}"
: "${MODEL_ID:?Set MODEL_ID to the served model name}"

mkdir -p "$artifact_dir"

python3 "$lesson_dir/src/verify_lock.py" \
  --lock "$lesson_dir/acceptance.lock.json" \
  --acceptance "$lesson_dir/data/acceptance.jsonl" \
  --config "$lesson_dir/configs/evaluation.json" \
  --evaluator "$lesson_dir/src/evaluate.py"

python3 "$lesson_dir/src/call_openai_endpoint.py" \
  --acceptance "$lesson_dir/data/acceptance.jsonl" \
  --config "$lesson_dir/configs/evaluation.json" \
  --output "$artifact_dir/endpoint-predictions.jsonl" \
  --base-url "$MODEL_BASE_URL" \
  --model "$MODEL_ID"

python3 "$lesson_dir/src/evaluate.py" \
  --acceptance "$lesson_dir/data/acceptance.jsonl" \
  --predictions "$artifact_dir/endpoint-predictions.jsonl" \
  --config "$lesson_dir/configs/evaluation.json" \
  --output "$artifact_dir/endpoint-results.json"

python3 "$lesson_dir/src/apply_gates.py" \
  --results "$artifact_dir/endpoint-results.json" \
  --gates "$lesson_dir/configs/release-gates.json" \
  --output "$artifact_dir/endpoint-release-decision.json"

printf 'Endpoint evidence written under %s\n' "$artifact_dir"
