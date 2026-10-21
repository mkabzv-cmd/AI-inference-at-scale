#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts
python3 bench/fake_server.py >artifacts/fake-server.log 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT
for _ in {1..20}; do
  curl --fail --silent http://127.0.0.1:18000/v1/models >/dev/null && break
  sleep 0.2
done
python3 bench/benchmark.py \
  --base-url http://127.0.0.1:18000 \
  --engine-name fake \
  --engine-version cpu-self-test \
  --mode closed \
  --concurrency 2 \
  --warmup-requests 1 \
  --measured-requests 4 \
  --max-tokens 16 \
  --tokenizer-mode whitespace-self-test \
  --output artifacts/fake.json
python3 bench/validate_results.py artifacts/fake.json --require-quality-rate 0
python3 bench/report.py artifacts/fake.json --output artifacts/report.md
grep -q '^# Benchmark report' artifacts/report.md
printf 'CPU benchmark self-test passed\n'
