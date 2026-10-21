#!/usr/bin/env bash
set -euo pipefail

container="${VLLM_CONTAINER:-oms-l17-vllm}"
if docker container inspect "$container" >/dev/null 2>&1; then
  docker stop "$container" >/dev/null
fi
if [[ "${DELETE_MODEL_CACHE:-0}" == "1" ]] &&
   docker volume inspect oms-l17-model-cache >/dev/null 2>&1; then
  docker volume rm oms-l17-model-cache >/dev/null
fi
echo "container removed; model cache retained unless DELETE_MODEL_CACHE=1"
