#!/usr/bin/env bash
set -euo pipefail

for name in oms-l19-baseline oms-l19-quantized; do
  docker stop "$name" >/dev/null 2>&1 || true
done
if [[ "${DELETE_MODEL_CACHE:-0}" == "1" ]]; then
  docker volume rm oms-l19-model-cache >/dev/null 2>&1 || true
fi
echo "comparison containers removed"
