#!/usr/bin/env bash
set -euo pipefail

: "${CPU_IMAGE_TAG:=open-models/llama-cpp:v0.5.0-cpu}"
mkdir -p artifacts
for model in qwen2.5-0.5b-instruct-q4_k_m.gguf qwen2.5-0.5b-instruct-q8_0.gguf; do
  test -f "artifacts/models/$model" || {
    echo "missing artifacts/models/$model" >&2
    exit 1
  }
  docker run --rm \
    --mount "type=bind,src=$(pwd)/artifacts/models,dst=/models,readonly" \
    --entrypoint llama-bench \
    "$CPU_IMAGE_TAG" \
    -m "/models/$model" \
    -ngl 0 \
    -t 4 \
    -p 512 \
    -n 64 \
    -r 3 \
    -o json \
    >"artifacts/llama-bench-${model%.gguf}.json"
done
printf 'wrote controlled Q4_K_M versus Q8_0 benchmark records\n'
