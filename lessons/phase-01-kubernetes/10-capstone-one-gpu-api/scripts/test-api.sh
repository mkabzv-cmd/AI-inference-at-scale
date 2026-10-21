#!/usr/bin/env bash
set -euo pipefail

namespace="${LAB_NAMESPACE:-one-gpu-api}"
release="${HELM_RELEASE:-one-gpu}"
local_port="${LOCAL_PORT:-18000}"
base_url="http://127.0.0.1:${local_port}"

mkdir -p artifacts
service="$(
  kubectl -n "$namespace" get service \
    -l "app.kubernetes.io/instance=${release}" \
    -o jsonpath='{.items[0].metadata.name}'
)"
if [[ -z "$service" ]]; then
  printf 'no Service found for Helm release %s\n' "$release" >&2
  exit 1
fi

kubectl -n "$namespace" port-forward \
  "service/${service}" "${local_port}:80" \
  >artifacts/port-forward.log 2>&1 &
forward_pid=$!
trap 'kill "$forward_pid" 2>/dev/null || true' EXIT

for _attempt in {1..60}; do
  if curl --fail --silent "${base_url}/health/ready" >/dev/null; then
    break
  fi
  sleep 1
done
curl --fail --silent --show-error "${base_url}/health/ready" >/dev/null

curl --fail --silent --show-error "${base_url}/v1/models" \
  >artifacts/models.json

curl --fail --silent --show-error \
  -H 'Content-Type: application/json' \
  --data @requests/chat-completion.json \
  "${base_url}/v1/chat/completions" \
  >artifacts/chat-completion.json

python3 - <<'PY'
import json
from pathlib import Path

models = json.loads(Path("artifacts/models.json").read_text())
response = json.loads(Path("artifacts/chat-completion.json").read_text())
assert models["object"] == "list"
assert models["data"][0]["id"] == "Qwen/Qwen2.5-0.5B-Instruct"
assert response["object"] == "chat.completion"
assert response["model"] == "Qwen/Qwen2.5-0.5B-Instruct"
assert response["choices"][0]["message"]["role"] == "assistant"
assert response["choices"][0]["message"]["content"].strip()
assert response["usage"]["completion_tokens"] > 0
print(json.dumps(response, indent=2))
print("non-streaming contract: PASS")
PY

curl --fail --silent --show-error --no-buffer \
  -H 'Content-Type: application/json' \
  --data @requests/chat-stream.json \
  "${base_url}/v1/chat/completions" \
  >artifacts/chat-stream.txt

grep -q '^data: ' artifacts/chat-stream.txt
grep -q '"content"' artifacts/chat-stream.txt
grep -q 'data: \[DONE\]' artifacts/chat-stream.txt
if grep -q '"error"' artifacts/chat-stream.txt; then
  printf 'stream returned an SSE error event\n' >&2
  exit 1
fi
curl --fail --silent --show-error "${base_url}/metrics" \
  >artifacts/metrics.txt
grep -q 'teaching_api_requests_total' artifacts/metrics.txt
grep -q '^teaching_api_inflight_requests 0$' artifacts/metrics.txt
printf 'streaming and metrics contracts: PASS\n'
