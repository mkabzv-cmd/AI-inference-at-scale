#!/usr/bin/env bash
set -euo pipefail

lesson_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$lesson_root"
mkdir -p artifacts

python3 - <<'PY'
import json
from pathlib import Path

config = json.loads(Path("configs/lifecycle.json").read_text())
config["gradient_accumulation_steps"] = 2
Path("artifacts/incompatible-config.json").write_text(
    json.dumps(config, indent=2, sort_keys=True) + "\n"
)
PY

set +e
python3 src/lifecycle_simulator.py \
  --config artifacts/incompatible-config.json \
  --output artifacts/resumed \
  --resume artifacts/resumed/checkpoint-0005.json \
  > artifacts/expected-resume-failure.txt 2>&1
status=$?
set -e

if [[ "$status" -eq 0 ]]; then
  printf 'ERROR: incompatible resume unexpectedly succeeded\n' >&2
  exit 1
fi
grep -q 'checkpoint configuration mismatch' \
  artifacts/expected-resume-failure.txt
printf 'PASS: incompatible checkpoint resume failed closed\n'
