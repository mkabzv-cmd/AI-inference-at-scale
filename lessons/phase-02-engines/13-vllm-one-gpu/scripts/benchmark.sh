#!/usr/bin/env bash
set -euo pipefail

: "${BENCH_BASE_URL:=http://127.0.0.1:8000}"
: "${CONCURRENCY:=4}"
mkdir -p artifacts
python3 ../12-benchmarking-methodology/bench/benchmark.py \
  --base-url "$BENCH_BASE_URL" \
  --prompts ../12-benchmarking-methodology/bench/prompts.jsonl \
  --engine-name vllm \
  --engine-version 0.28.0 \
  --engine-config-json "{\"max_num_seqs\":16,\"gpu_memory_utilization\":0.8}" \
  --mode closed \
  --concurrency "$CONCURRENCY" \
  --warmup-requests 2 \
  --measured-requests 18 \
  --output "artifacts/results-c${CONCURRENCY}.json"
python3 ../12-benchmarking-methodology/bench/validate_results.py \
  "artifacts/results-c${CONCURRENCY}.json"
