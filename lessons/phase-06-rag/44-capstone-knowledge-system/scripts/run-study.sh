#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$lesson_dir"
mkdir -p artifacts
python3 src/study.py \
  --contract configs/study-contract.json \
  --questions data/study-questions.json \
  --work-dir artifacts/study \
  --output artifacts/study-results.json
