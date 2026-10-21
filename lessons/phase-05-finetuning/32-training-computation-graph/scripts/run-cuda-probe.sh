#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${ARTIFACT_DIR:-$lesson_dir/artifacts}"

if ! command -v nvidia-smi >/dev/null 2>&1; then
  printf 'nvidia-smi is unavailable; use run-cpu-lab.sh first\n' >&2
  exit 1
fi

python3 -c 'import torch; assert torch.cuda.is_available()' || {
  printf '%s\n' \
    'Install a compatible PyTorch build from the official selector first.' >&2
  exit 1
}

mkdir -p "$artifact_dir"

python3 "$lesson_dir/src/torch_cuda_probe.py" \
  --output "$artifact_dir/cuda-no-checkpoint.json"

python3 "$lesson_dir/src/torch_cuda_probe.py" \
  --checkpoint \
  --output "$artifact_dir/cuda-checkpoint.json"

printf 'Compare the two fresh-process measurements under %s\n' "$artifact_dir"
