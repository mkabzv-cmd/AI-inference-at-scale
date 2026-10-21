#!/usr/bin/env bash
set -euo pipefail

: "${BENCH_BASE_URL:=http://127.0.0.1:8000}"
: "${CONCURRENCY:=4}"
: "${RADIX_CACHE_ENABLED:=true}"
case "$RADIX_CACHE_ENABLED" in true|false) ;; *) exit 1 ;; esac
mkdir -p artifacts
python3 ../12-benchmarking-methodology/bench/benchmark.py \
  --base-url "$BENCH_BASE_URL" \
  --prompts ../12-benchmarking-methodology/bench/prompts.jsonl \
  --engine-name sglang \
  --engine-version 0.5.21 \
  --engine-config-json "{\"max_running_requests\":16,\"mem_fraction_static\":0.75,\"radix_cache\":${RADIX_CACHE_ENABLED}}" \
  --mode closed \
  --concurrency "$CONCURRENCY" \
  --warmup-requests 2 \
  --measured-requests 18 \
  --output "artifacts/results-c${CONCURRENCY}.json"
python3 ../12-benchmarking-methodology/bench/validate_results.py \
  "artifacts/results-c${CONCURRENCY}.json"
