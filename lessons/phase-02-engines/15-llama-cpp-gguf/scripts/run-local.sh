#!/usr/bin/env bash
set -euo pipefail

: "${CPU_IMAGE_TAG:=open-models/llama-cpp:v0.5.0-cpu}"
: "${GGUF_NAME:=qwen2.5-0.5b-instruct-q4_k_m.gguf}"
model_dir="$(pwd)/artifacts/models"
test -f "$model_dir/$GGUF_NAME" || {
  echo "download $GGUF_NAME first" >&2
  exit 1
}
exec docker run --rm --name open-models-l15 \
  --publish 127.0.0.1:8000:8000 \
  --mount "type=bind,src=$model_dir,dst=/models,readonly" \
  "$CPU_IMAGE_TAG" \
  --model "/models/$GGUF_NAME" \
  --alias course-model \
  --host 0.0.0.0 \
  --port 8000 \
  --ctx-size 4096 \
  --n-gpu-layers 0 \
  --threads 4 \
  --jinja
