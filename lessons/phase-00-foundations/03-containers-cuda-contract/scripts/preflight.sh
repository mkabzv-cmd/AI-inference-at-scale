#!/usr/bin/env bash
set -euo pipefail

for name in docker python3; do
  command -v "$name" >/dev/null 2>&1 || {
    printf '[fail] required command not found: %s\n' "$name"
    exit 1
  }
done
printf '[ok] docker client found: %s\n' "$(docker --version)"
docker info >/dev/null 2>&1 || {
  printf '[fail] docker daemon is not reachable by this user\n'
  exit 1
}
printf '[ok] docker daemon reachable\n'

if command -v nvidia-smi >/dev/null 2>&1; then
  printf '[info] host NVIDIA summary:\n'
  if ! nvidia-smi \
    --query-gpu=index,name,driver_version,memory.total \
    --format=csv,noheader; then
    printf '[warn] nvidia-smi exists but its GPU query failed; GPU proof is unavailable\n'
  fi
else
  printf '[info] nvidia-smi not found; no-GPU path still works\n'
fi

available_kib="$(df -Pk . | awk 'NR==2 {print $4}')"
if (( available_kib < 6 * 1024 * 1024 )); then
  printf '[warn] less than 6 GiB free; the teaching image may not fit\n'
else
  printf '[ok] at least 6 GiB filesystem space is available\n'
fi
