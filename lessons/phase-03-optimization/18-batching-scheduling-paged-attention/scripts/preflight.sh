#!/usr/bin/env bash
set -euo pipefail

command -v python3 >/dev/null
python3 - <<'PY'
import sys
if sys.version_info < (3, 9):
    raise SystemExit("Python 3.9 or newer is required")
print("python:", sys.version.split()[0])
PY
python3 -m json.tool configs/workload.json >/dev/null
python3 -m json.tool configs/experiment-matrix.json >/dev/null
python3 -m json.tool results.schema.json >/dev/null
echo "lesson 18 CPU preflight passed"
