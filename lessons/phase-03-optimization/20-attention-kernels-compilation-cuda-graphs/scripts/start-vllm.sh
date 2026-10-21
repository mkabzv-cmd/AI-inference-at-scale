#!/usr/bin/env bash
set -euo pipefail

: "${VLLM_IMAGE:?set immutable image name@sha256 digest}"
[[ "$VLLM_IMAGE" =~ ^[A-Za-z0-9][A-Za-z0-9./:_-]*@sha256:[0-9a-f]{64}$ ]] || {
  echo "VLLM_IMAGE must be an immutable name@sha256 digest" >&2
  exit 2
}
config="${1:-configs/vllm-eager.args}"
[[ -f "$config" ]] || { echo "missing $config" >&2; exit 2; }
args=()
while IFS= read -r line; do [[ -n "$line" ]] && args+=("$line"); done < "$config"
docker run --detach --rm \
  --name oms-l20-vllm \
  --gpus all \
  --shm-size=4g \
  --publish 127.0.0.1:8000:8000 \
  --volume oms-l20-model-cache:/root/.cache/huggingface \
  "$VLLM_IMAGE" \
  Qwen/Qwen2.5-0.5B-Instruct \
  "${args[@]}"
echo "started $config; save startup logs before benchmarking"
