#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts
docker logs oms-l20-vllm > artifacts/vllm-startup.log 2>&1
nvidia-smi \
  --query-gpu=timestamp,name,driver_version,memory.total,memory.used,utilization.gpu \
  --format=csv |
  tee artifacts/gpu-snapshot.csv
if command -v nsys >/dev/null; then
  nsys --version | tee artifacts/nsys-version.txt
  echo "Run the engine under nsys from a reviewed host/container setup; do not"
  echo "mistake this snapshot for a kernel trace."
else
  echo "nsys absent: retain logs and GPU snapshot; GPU trace is not claimed."
fi
