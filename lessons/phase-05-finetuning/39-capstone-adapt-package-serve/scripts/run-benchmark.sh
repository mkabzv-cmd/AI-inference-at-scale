#!/usr/bin/env bash
set -euo pipefail

: "${BENCH_BASE_URL:=http://127.0.0.1:8000}"
: "${ENGINE_NAME:?Set the Phase-2 engine name}"
: "${ENGINE_VERSION:?Set the exact engine version}"
: "${ENGINE_CONFIG_JSON:={}}"
: "${SERVER_FINGERPRINT:?Set the immutable image digest}"
: "${BENCH_GPU_NAME:?Set the exact GPU name from nvidia-smi}"
: "${MODEL_ID:?Set the served base or tuned model name}"
: "${MODEL_REVISION:?Set the immutable base model revision}"

label="${1:?Pass base or tuned}"
case "$label" in base|tuned) ;; *) printf 'label must be base or tuned\n' >&2; exit 1 ;; esac
lesson_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
benchmark_root="$lesson_root/../../phase-02-engines/12-benchmarking-methodology"
mkdir -p "$lesson_root/artifacts/benchmark"
python3 "$benchmark_root/bench/benchmark.py" \
  --base-url "$BENCH_BASE_URL" \
  --prompts "$benchmark_root/bench/prompts.jsonl" \
  --engine-name "$ENGINE_NAME" \
  --engine-version "$ENGINE_VERSION" \
  --engine-config-json "$ENGINE_CONFIG_JSON" \
  --model-id "$MODEL_ID" \
  --model-revision "$MODEL_REVISION" \
  --served-model-name "$MODEL_ID" \
  --artifact "$label" \
  --mode closed \
  --concurrency 1 \
  --warmup-requests 3 \
  --measured-requests 24 \
  --max-tokens 64 \
  --temperature 0 \
  --seed 42 \
  --gpu-name "$BENCH_GPU_NAME" \
  --server-fingerprint "$SERVER_FINGERPRINT" \
  --output "$lesson_root/artifacts/benchmark/$label.json"
python3 "$benchmark_root/bench/validate_results.py" \
  "$lesson_root/artifacts/benchmark/$label.json"
