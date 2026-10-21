#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:=open-models-l11}"
mkdir -p artifacts
kubectl port-forward --address 127.0.0.1 \
  -n "$LAB_NAMESPACE" service/transformers-baseline 8000:8000 \
  >artifacts/port-forward.log 2>&1 &
forward_pid=$!
trap 'kill "$forward_pid" 2>/dev/null || true' EXIT

for _ in {1..30}; do
  curl --fail --silent http://127.0.0.1:8000/health/ready >/dev/null && break
  sleep 1
done

curl --fail --silent --show-error \
  -H 'content-type: application/json' \
  --data @requests/chat.json \
  http://127.0.0.1:8000/v1/chat/completions \
  >artifacts/chat-response.json

python3 - <<'PY'
import json
from pathlib import Path

result = json.loads(Path("artifacts/chat-response.json").read_text())
assert result["object"] == "chat.completion"
assert result["choices"][0]["message"]["content"].strip()
assert result["usage"]["prompt_tokens"] > 0
assert result["usage"]["completion_tokens"] > 0
trace = result["teaching_trace"]
assert trace["input_shape"][0] == 1
assert trace["output_shape"][1] > trace["input_shape"][1]
print("non-streaming behavioral check passed")
PY

curl --fail --silent --show-error --no-buffer \
  -H 'content-type: application/json' \
  --data @requests/chat-stream.json \
  http://127.0.0.1:8000/v1/chat/completions \
  >artifacts/chat-stream.txt
grep -q '^data: {' artifacts/chat-stream.txt
grep -q '^data: \[DONE\]' artifacts/chat-stream.txt
curl --fail --silent http://127.0.0.1:8000/debug/runtime \
  >artifacts/runtime.json
curl --fail --silent http://127.0.0.1:8000/metrics \
  >artifacts/metrics.txt
grep -q 'transformers_baseline_requests_total' artifacts/metrics.txt
printf 'streaming, runtime, and metrics checks passed\n'
