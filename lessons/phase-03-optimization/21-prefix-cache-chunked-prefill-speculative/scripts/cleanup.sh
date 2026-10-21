#!/usr/bin/env bash
set -euo pipefail

docker stop oms-l21-vllm >/dev/null 2>&1 || true
if [[ "${DELETE_MODEL_CACHE:-0}" == "1" ]]; then
  docker volume rm oms-l21-model-cache >/dev/null 2>&1 || true
fi
echo "lesson 21 server removed"
