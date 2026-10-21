#!/usr/bin/env bash
set -euo pipefail

python_command="${PYTHON_COMMAND:-.venv/bin/python}"
if [[ ! -x "$python_command" ]]; then
  printf 'Python environment not found: %s\n' "$python_command" >&2
  printf 'Create it using the Preflight instructions in README.md.\n' >&2
  exit 2
fi

mkdir -p results

"$python_command" src/generate.py \
  --prompt 'The capital of France is' \
  --max-new-tokens 8 \
  --mode greedy \
  --compare-high-level \
  --output results/greedy.json

"$python_command" src/generate.py \
  --prompt 'Once upon a time' \
  --max-new-tokens 20 \
  --mode sample \
  --temperature 0.8 \
  --top-k 40 \
  --top-p 0.9 \
  --seed 123 \
  --output results/sample-a.json

"$python_command" src/generate.py \
  --prompt 'Once upon a time' \
  --max-new-tokens 20 \
  --mode sample \
  --temperature 0.8 \
  --top-k 40 \
  --top-p 0.9 \
  --seed 123 \
  --output results/sample-b.json

"$python_command" scripts/verify-results.py results
