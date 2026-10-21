#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${ARTIFACT_DIR:-$lesson_dir/artifacts}"

mkdir -p "$artifact_dir"

python3 "$lesson_dir/src/verify_lock.py" \
  --lock "$lesson_dir/acceptance.lock.json" \
  --acceptance "$lesson_dir/data/acceptance.jsonl" \
  --config "$lesson_dir/configs/evaluation.json" \
  --evaluator "$lesson_dir/src/evaluate.py"

python3 "$lesson_dir/src/evaluate.py" \
  --acceptance "$lesson_dir/data/acceptance.jsonl" \
  --predictions "$lesson_dir/data/base-predictions.jsonl" \
  --config "$lesson_dir/configs/evaluation.json" \
  --output "$artifact_dir/base-results.json"

python3 "$lesson_dir/src/apply_gates.py" \
  --results "$artifact_dir/base-results.json" \
  --gates "$lesson_dir/configs/release-gates.json" \
  --output "$artifact_dir/base-release-decision.json"

python3 "$lesson_dir/scripts/verify_baseline.py" \
  --results "$artifact_dir/base-results.json" \
  --decision "$artifact_dir/base-release-decision.json"

printf 'Baseline evidence written under %s\n' "$artifact_dir"
