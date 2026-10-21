#!/usr/bin/env bash
set -euo pipefail

: "${VLLM_IMAGE:?set immutable vllm/vllm-openai@sha256:...}"
: "${QUANT_MODEL_ID:?set a reviewed quantized model repository}"
: "${QUANT_MODEL_REVISION:?set its exact 40-character commit}"
[[ "$VLLM_IMAGE" =~ ^[A-Za-z0-9][A-Za-z0-9./:_-]*@sha256:[0-9a-f]{64}$ ]] || {
  echo "VLLM_IMAGE must be an immutable name@sha256 digest" >&2
  exit 2
}
[[ "$QUANT_MODEL_REVISION" =~ ^[0-9a-f]{40}$ ]] || {
  echo "QUANT_MODEL_REVISION must be a 40-character commit" >&2
  exit 2
}
port="${PORT:-8001}"
name="${CONTAINER_NAME:-oms-l19-quantized}"
if [[ ! "$port" =~ ^[0-9]+$ ]] ||
  (( port < 1024 || port > 65535 )); then
  echo "PORT must be an integer from 1024 through 65535" >&2
  exit 2
fi
docker run --detach --rm \
  --name "$name" \
  --gpus all \
  --shm-size=4g \
  --publish "127.0.0.1:${port}:8000" \
  --volume oms-l19-model-cache:/root/.cache/huggingface \
  "$VLLM_IMAGE" \
  "$QUANT_MODEL_ID" \
  --revision "$QUANT_MODEL_REVISION" \
  --served-model-name oms-quantized \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.80 \
  --max-num-seqs 8
echo "started $name on http://127.0.0.1:$port"
