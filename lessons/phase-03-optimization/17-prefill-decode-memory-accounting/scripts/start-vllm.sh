#!/usr/bin/env bash
set -euo pipefail

: "${VLLM_IMAGE:?set VLLM_IMAGE to an immutable name@sha256 digest}"
[[ "$VLLM_IMAGE" =~ ^[A-Za-z0-9][A-Za-z0-9./:_-]*@sha256:[0-9a-f]{64}$ ]] || {
  echo "VLLM_IMAGE must be an immutable name@sha256 digest" >&2
  exit 1
}

container="${VLLM_CONTAINER:-oms-l17-vllm}"
model="${MODEL_ID:-Qwen/Qwen2.5-0.5B-Instruct}"
revision="${MODEL_REVISION:-7ae557604adf67be50417f59c2c2f167def9a775}"

docker run --detach --rm \
  --name "$container" \
  --gpus all \
  --shm-size=4g \
  --publish 127.0.0.1:8000:8000 \
  --volume oms-l17-model-cache:/root/.cache/huggingface \
  "$VLLM_IMAGE" \
  "$model" \
  --revision "$revision" \
  --served-model-name oms-model \
  --dtype half \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.80 \
  --max-num-seqs 16

echo "started $container; inspect startup with: docker logs -f $container"
