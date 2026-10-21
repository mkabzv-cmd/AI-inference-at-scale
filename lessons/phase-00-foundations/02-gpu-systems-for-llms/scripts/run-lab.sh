#!/usr/bin/env bash
set -euo pipefail

python_command="${PYTHON_COMMAND:-.venv/bin/python}"
if [[ ! -x "$python_command" ]]; then
  printf 'Python environment not found: %s\n' "$python_command" >&2
  exit 2
fi
mkdir -p results

"$python_command" src/memory_budget.py \
  --params-billion 7 --weight-bits 16 \
  --layers 32 --kv-heads 32 --head-dim 128 \
  --sequences 1 --tokens-per-sequence 2048 --kv-bits 16 \
  --vram-gib 24 --output results/memory-7b.json

"$python_command" src/memory_budget.py \
  --params-billion 7 --weight-bits 16 \
  --layers 32 --kv-heads 32 --head-dim 128 \
  --sequences 8 --tokens-per-sequence 2048 --kv-bits 16 \
  --vram-gib 24 --output results/memory-7b-8seq.json

"$python_command" src/hardware_report.py --output results/hardware.json
"$python_command" src/benchmark.py \
  --device cpu --matrix-size 1024 --copy-mebibytes 64 \
  --warmup 3 --iterations 10 --output results/benchmark-cpu.json

"$python_command" scripts/verify-results.py results
