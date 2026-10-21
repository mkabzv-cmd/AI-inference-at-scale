#!/usr/bin/env bash
set -euo pipefail

command -v python3 >/dev/null
python3 - <<'PY'
import sys
if sys.version_info < (3, 9):
    raise SystemExit("Python 3.9 or newer is required")
print("python:", sys.version.split()[0])
PY

python3 -m json.tool configs/model.json >/dev/null
python3 -m json.tool configs/workloads.json >/dev/null
python3 -m json.tool results.schema.json >/dev/null

if [[ "${RUN_GPU_TRACK:-0}" == "1" ]]; then
  command -v docker >/dev/null
  command -v curl >/dev/null
  command -v nvidia-smi >/dev/null
  docker info >/dev/null
  nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
fi

echo "lesson 17 preflight passed"
