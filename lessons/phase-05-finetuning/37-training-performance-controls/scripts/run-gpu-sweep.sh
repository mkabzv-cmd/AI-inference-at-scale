#!/usr/bin/env bash
set -euo pipefail

: "${ALLOW_LESSON_37_GPU_SWEEP:?Set ALLOW_LESSON_37_GPU_SWEEP=yes}"
if [[ "$ALLOW_LESSON_37_GPU_SWEEP" != "yes" ]]; then
  printf 'Refusing: ALLOW_LESSON_37_GPU_SWEEP must equal yes\n' >&2
  exit 1
fi

lesson_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dataset_dir="${1:-$lesson_root/../33-dataset-engineering-chat-templates/artifacts/dataset}"
test -f "$dataset_dir/manifest.json"
cd "$lesson_root"
python3 src/run_transformers_sweep.py \
  --study configs/study.json \
  --dataset-dir "$dataset_dir" \
  --output artifacts/gpu-sweep \
  --allow-gpu-run
