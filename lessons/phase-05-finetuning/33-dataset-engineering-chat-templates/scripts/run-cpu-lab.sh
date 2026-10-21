#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${ARTIFACT_DIR:-$lesson_dir/artifacts}"
dataset_dir="$artifact_dir/dataset"

mkdir -p "$artifact_dir"

python3 "$lesson_dir/src/build_dataset.py" \
  --input "$lesson_dir/data/raw/examples.jsonl" \
  --config "$lesson_dir/configs/dataset.json" \
  --output-dir "$dataset_dir"

python3 "$lesson_dir/src/audit_dataset.py" \
  --dataset-dir "$dataset_dir"

python3 "$lesson_dir/src/packing_report.py" \
  --dataset-dir "$dataset_dir" \
  --max-length 1024 \
  --output "$artifact_dir/packing-report.json"

printf 'Evidence written under %s\n' "$artifact_dir"
