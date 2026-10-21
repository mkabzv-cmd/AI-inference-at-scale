#!/usr/bin/env bash
set -euo pipefail

name="${CONTAINER_NAME:-oms-l19-quantized}"
docker logs "$name" 2>&1 | tee artifacts/engine-startup.log
docker exec -i "$name" python3 - <<'PY'
import importlib.metadata
for package in ("torch", "vllm"):
    print(package, importlib.metadata.version(package))
PY
nvidia-smi \
  --query-compute-apps=pid,used_memory \
  --format=csv,noheader |
  tee artifacts/gpu-process-memory.csv
