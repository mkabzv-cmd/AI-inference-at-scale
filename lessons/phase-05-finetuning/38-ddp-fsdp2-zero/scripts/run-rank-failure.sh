#!/usr/bin/env bash
set -euo pipefail

lesson_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$lesson_root"
mkdir -p artifacts
set +e
torchrun --standalone --nnodes=1 --nproc-per-node=3 \
  src/rank_failure.py > artifacts/rank-failure.log 2>&1
status=$?
set -e
if [[ "$status" -eq 0 ]]; then
  printf 'ERROR: intentional rank failure returned success\n' >&2
  exit 1
fi
grep -q 'intentional rank-1 exit' artifacts/rank-failure.log
printf 'PASS: one failed rank terminates the distributed worker group\n'
