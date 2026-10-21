#!/usr/bin/env bash
set -euo pipefail
mkdir -p artifacts
python3 src/arithmetic_fixture.py \
  --output artifacts/arithmetic-fixture.json
python3 - <<'PY'
import json
from pathlib import Path

d = json.loads(Path("artifacts/arithmetic-fixture.json").read_text())
assert d["correctness"]["passed"] is True
assert d["measurements"]["full_output"] == d["measurements"]["reduced_output"]
print("row-shard arithmetic fixture: PASS")
PY
