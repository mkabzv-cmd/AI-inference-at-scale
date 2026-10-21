#!/usr/bin/env bash
set -euo pipefail
: "${LAB_NAMESPACE:?set LAB_NAMESPACE}"
: "${SERVED_MODEL_NAME:?set SERVED_MODEL_NAME}"
local_port="${LOCAL_PORT:-18029}"
if [[ ! "$local_port" =~ ^[0-9]+$ ]] ||
  (( local_port < 1024 || local_port > 65535 )); then
  printf 'LOCAL_PORT must be an integer from 1024 through 65535\n' >&2
  exit 2
fi
mkdir -p artifacts

python3 - requests/completion.json artifacts/request.rendered.json \
  "$SERVED_MODEL_NAME" <<'PY'
import json
import sys
from pathlib import Path
source, output, model = sys.argv[1:]
d = json.loads(Path(source).read_text())
d["model"] = model
Path(output).write_text(json.dumps(d) + "\n")
PY
kubectl -n "$LAB_NAMESPACE" port-forward --address 127.0.0.1 \
  service/vllm-pp-api "${local_port}:80" \
  >artifacts/benchmark-port-forward.log 2>&1 &
forward_pid=$!
stop_forward() {
  kill "$forward_pid" >/dev/null 2>&1 || true
  wait "$forward_pid" >/dev/null 2>&1 || true
}
trap stop_forward EXIT
healthy=false
for _attempt in {1..60}; do
  if curl --fail --silent "http://127.0.0.1:${local_port}/health" \
    >/dev/null 2>&1; then
    healthy=true
    break
  fi
  sleep 2
done
[[ "$healthy" == "true" ]] || {
  printf 'port-forwarded API did not become healthy\n' >&2
  exit 1
}
python3 src/request_benchmark.py \
  --url "http://127.0.0.1:${local_port}/v1/completions" \
  --request artifacts/request.rendered.json \
  --requests "${BENCHMARK_REQUESTS:-6}" \
  --concurrency "${BENCHMARK_CONCURRENCY:-2}" \
  --output artifacts/benchmark.json
