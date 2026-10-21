#!/usr/bin/env bash
set -euo pipefail

: "${BENCH_BASE_URL:=http://127.0.0.1:8000}"
: "${ENGINE_NAME:?set ENGINE_NAME to transformers, vllm, sglang, or llama-cpp}"
: "${ENGINE_VERSION:?set exact ENGINE_VERSION}"
: "${ENGINE_CONFIG_JSON:={}}"
: "${SERVER_FINGERPRINT:?set SERVER_FINGERPRINT to the image digest or build commit}"
: "${BENCH_GPU_NAME:?set BENCH_GPU_NAME from nvidia-smi}"
case "$ENGINE_NAME" in transformers|vllm|sglang|llama-cpp) ;; *) exit 1 ;; esac

mkdir -p "artifacts/raw/$ENGINE_NAME"
for concurrency in 1 4 16; do
  for repeat in 1 2 3; do
    output="artifacts/raw/$ENGINE_NAME/closed-c${concurrency}-r${repeat}.json"
    python3 ../12-benchmarking-methodology/bench/benchmark.py \
      --base-url "$BENCH_BASE_URL" \
      --prompts ../12-benchmarking-methodology/bench/prompts.jsonl \
      --engine-name "$ENGINE_NAME" \
      --engine-version "$ENGINE_VERSION" \
      --engine-config-json "$ENGINE_CONFIG_JSON" \
      --mode closed \
      --concurrency "$concurrency" \
      --warmup-requests 3 \
      --measured-requests 24 \
      --max-tokens 64 \
      --temperature 0 \
      --seed 42 \
      --gpu-name "$BENCH_GPU_NAME" \
      --server-fingerprint "$SERVER_FINGERPRINT" \
      --output "$output"
    python3 ../12-benchmarking-methodology/bench/validate_results.py "$output"
  done
done

for repeat in 1 2 3; do
  output="artifacts/raw/$ENGINE_NAME/open-rps4-r${repeat}.json"
  python3 ../12-benchmarking-methodology/bench/benchmark.py \
    --base-url "$BENCH_BASE_URL" \
    --prompts ../12-benchmarking-methodology/bench/prompts.jsonl \
    --engine-name "$ENGINE_NAME" \
    --engine-version "$ENGINE_VERSION" \
    --engine-config-json "$ENGINE_CONFIG_JSON" \
    --mode open \
    --request-rate 4 \
    --concurrency 64 \
    --warmup-requests 3 \
    --measured-requests 40 \
    --max-tokens 64 \
    --temperature 0 \
    --seed 42 \
    --gpu-name "$BENCH_GPU_NAME" \
    --server-fingerprint "$SERVER_FINGERPRINT" \
    --output "$output"
  python3 ../12-benchmarking-methodology/bench/validate_results.py "$output"
done
printf 'captured complete matrix for %s\n' "$ENGINE_NAME"
