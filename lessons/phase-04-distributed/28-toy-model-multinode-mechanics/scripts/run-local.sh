#!/usr/bin/env bash
set -euo pipefail
command -v torchrun >/dev/null 2>&1 || {
  printf 'activate the lesson venv; torchrun is missing\n' >&2
  exit 2
}
mkdir -p artifacts/local
torchrun --standalone --nproc-per-node=3 \
  src/toy_tp.py \
  --backend gloo \
  --output artifacts/local/summary.json
python3 - <<'PY'
import json
from pathlib import Path

d = json.loads(Path("artifacts/local/summary.json").read_text())
assert d["correctness"]["passed"] is True
assert d["measurements"]["max_absolute_error"] <= 1e-5
print("local toy TP: PASS")
PY
