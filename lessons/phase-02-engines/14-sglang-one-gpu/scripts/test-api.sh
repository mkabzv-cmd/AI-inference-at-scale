#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:=open-models-l14}"
mkdir -p artifacts
kubectl port-forward --address 127.0.0.1 \
  -n "$LAB_NAMESPACE" service/sglang 8000:8000 \
  >artifacts/port-forward.log 2>&1 &
pid=$!
trap 'kill "$pid" 2>/dev/null || true' EXIT
for _ in {1..30}; do
  curl --fail --silent http://127.0.0.1:8000/health >/dev/null && break
  sleep 1
done
curl --fail --silent http://127.0.0.1:8000/v1/models >artifacts/models.json
curl --fail --silent --show-error \
  -H 'content-type: application/json' \
  --data @requests/smoke.json \
  http://127.0.0.1:8000/v1/chat/completions >artifacts/smoke-response.json
curl --fail --silent --show-error \
  -H 'content-type: application/json' \
  --data @requests/structured.json \
  http://127.0.0.1:8000/v1/chat/completions >artifacts/structured-response.json
python3 - <<'PY'
import json
from pathlib import Path
models = json.loads(Path("artifacts/models.json").read_text())
result = json.loads(Path("artifacts/smoke-response.json").read_text())
structured = json.loads(Path("artifacts/structured-response.json").read_text())
payload = json.loads(structured["choices"][0]["message"]["content"])
assert any(model["id"] == "course-model" for model in models["data"])
assert result["choices"][0]["message"]["content"].strip()
assert set(payload) == {"category", "next_action"}
assert all(isinstance(value, str) and value.strip() for value in payload.values())
print("SGLang behavioral check passed")
PY
