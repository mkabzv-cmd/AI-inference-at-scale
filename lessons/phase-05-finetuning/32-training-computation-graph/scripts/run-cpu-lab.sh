#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${ARTIFACT_DIR:-$lesson_dir/artifacts}"

mkdir -p "$artifact_dir"

python3 "$lesson_dir/src/train_trace.py" \
  --output "$artifact_dir/training-trace.json" \
  --steps 120 \
  --seed 3201

python3 "$lesson_dir/src/memory_accounting.py" \
  --cases "$lesson_dir/configs/memory-cases.json" \
  --output "$artifact_dir/memory-accounting.json"

python3 "$lesson_dir/scripts/verify.py" \
  --trace "$artifact_dir/training-trace.json" \
  --memory "$artifact_dir/memory-accounting.json"

printf 'Evidence written under %s\n' "$artifact_dir"
