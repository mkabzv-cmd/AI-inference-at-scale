#!/usr/bin/env bash
set -euo pipefail

mkdir -p artifacts
curl --fail --silent --show-error http://127.0.0.1:8000/v1/models \
  >artifacts/models.json
curl --fail --silent --show-error \
  -H 'content-type: application/json' \
  --data @requests/smoke.json \
  http://127.0.0.1:8000/v1/chat/completions \
  >artifacts/smoke-response.json
python3 - <<'PY'
import json
from pathlib import Path
models = json.loads(Path("artifacts/models.json").read_text())
response = json.loads(Path("artifacts/smoke-response.json").read_text())
assert any(model["id"] == "course-model" for model in models["data"])
assert response["choices"][0]["message"]["content"].strip()
print("llama.cpp behavioral check passed")
PY
