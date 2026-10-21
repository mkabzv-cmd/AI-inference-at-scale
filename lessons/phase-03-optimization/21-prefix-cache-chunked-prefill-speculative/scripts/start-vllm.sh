#!/usr/bin/env bash
set -euo pipefail

: "${VLLM_IMAGE:?set immutable vllm image name@sha256 digest}"
[[ "$VLLM_IMAGE" =~ ^[A-Za-z0-9][A-Za-z0-9./:_-]*@sha256:[0-9a-f]{64}$ ]] || {
  echo "VLLM_IMAGE must be an immutable name@sha256 digest" >&2
  exit 2
}
args=()
while IFS= read -r line; do
  [[ -n "$line" ]] && args+=("$line")
done < configs/vllm-prefix-chunked.args
docker run --detach --rm \
  --name oms-l21-vllm \
  --gpus all \
  --shm-size=4g \
  --publish 127.0.0.1:8000:8000 \
  --volume oms-l21-model-cache:/root/.cache/huggingface \
  "$VLLM_IMAGE" \
  Qwen/Qwen2.5-0.5B-Instruct \
  "${args[@]}"
echo "prefix caching + chunked prefill server started"
