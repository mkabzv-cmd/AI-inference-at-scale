#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:=open-models-l13}"
mkdir -p artifacts
kubectl port-forward --address 127.0.0.1 \
  -n "$LAB_NAMESPACE" service/vllm 8000:8000 \
  >artifacts/port-forward.log 2>&1 &
pid=$!
trap 'kill "$pid" 2>/dev/null || true' EXIT
for _ in {1..30}; do
  curl --fail --silent http://127.0.0.1:8000/health >/dev/null && break
  sleep 1
done
curl --fail --silent --show-error http://127.0.0.1:8000/v1/models \
  >artifacts/models.json
curl --fail --silent --show-error \
  -H 'content-type: application/json' \
  --data @requests/smoke.json \
  http://127.0.0.1:8000/v1/chat/completions \
  >artifacts/smoke-response.json
curl --fail --silent --show-error http://127.0.0.1:8000/metrics \
  >artifacts/metrics.txt
python3 - <<'PY'
import json
from pathlib import Path
models = json.loads(Path("artifacts/models.json").read_text())
response = json.loads(Path("artifacts/smoke-response.json").read_text())
assert any(item["id"] == "course-model" for item in models["data"])
assert response["choices"][0]["message"]["content"].strip()
assert response["usage"]["completion_tokens"] > 0
print("vLLM behavioral check passed")
PY
grep -Eq 'vllm:|vllm_' artifacts/metrics.txt
