#!/usr/bin/env bash
set -euo pipefail

: "${BENCH_BASE_URL:=http://127.0.0.1:8000}"
: "${ENGINE_NAME:?set ENGINE_NAME}"
: "${ENGINE_VERSION:?set ENGINE_VERSION}"
: "${REQUEST_RATE:=2}"
: "${MAX_INFLIGHT:=64}"
mkdir -p artifacts
python3 bench/benchmark.py \
  --base-url "$BENCH_BASE_URL" \
  --engine-name "$ENGINE_NAME" \
  --engine-version "$ENGINE_VERSION" \
  --mode open \
  --request-rate "$REQUEST_RATE" \
  --concurrency "$MAX_INFLIGHT" \
  --warmup-requests 2 \
  --measured-requests 24 \
  --max-tokens 64 \
  --output "artifacts/${ENGINE_NAME}-open-rps${REQUEST_RATE}.json"
