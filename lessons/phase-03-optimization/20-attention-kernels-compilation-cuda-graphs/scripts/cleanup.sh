#!/usr/bin/env bash
set -euo pipefail

docker stop oms-l20-vllm >/dev/null 2>&1 || true
if [[ "${DELETE_MODEL_CACHE:-0}" == "1" ]]; then
  docker volume rm oms-l20-model-cache >/dev/null 2>&1 || true
fi
echo "lesson 20 engine stopped"
