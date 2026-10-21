#!/usr/bin/env bash
set -euo pipefail

: "${BENCH_BASE_URL:=http://127.0.0.1:8000}"
: "${ENGINE_NAME:?set ENGINE_NAME}"
: "${ENGINE_VERSION:?set ENGINE_VERSION}"
: "${CONCURRENCY:=1}"
mkdir -p artifacts
python3 bench/benchmark.py \
  --base-url "$BENCH_BASE_URL" \
  --engine-name "$ENGINE_NAME" \
  --engine-version "$ENGINE_VERSION" \
  --mode closed \
  --concurrency "$CONCURRENCY" \
  --warmup-requests 2 \
  --measured-requests 12 \
  --max-tokens 64 \
  --output "artifacts/${ENGINE_NAME}-closed-c${CONCURRENCY}.json"
