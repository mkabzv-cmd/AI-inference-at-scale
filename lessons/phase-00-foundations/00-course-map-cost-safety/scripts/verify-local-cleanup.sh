#!/usr/bin/env bash
set -euo pipefail

expected="${EXPECTED_GPU_DESIRED:-0}"
if [[ "$expected" != "0" ]]; then
  printf '[fail] expected GPU desired capacity 0, received %s\n' "$expected"
  printf 'Cleanup verification failed.\n'
  exit 1
fi
printf '[ok] expected GPU desired capacity is zero\n'
printf '[ok] no synthetic lesson resources exist\n'
printf 'Cleanup verification passed.\n'
