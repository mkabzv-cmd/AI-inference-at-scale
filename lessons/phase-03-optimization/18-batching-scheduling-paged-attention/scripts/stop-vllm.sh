#!/usr/bin/env bash
set -euo pipefail

docker stop oms-l18-vllm >/dev/null 2>&1 || true
if [[ "${DELETE_MODEL_CACHE:-0}" == "1" ]]; then
  docker volume rm oms-l18-model-cache >/dev/null 2>&1 || true
fi
echo "lesson 18 engine stopped"
