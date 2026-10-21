#!/usr/bin/env bash
set -euo pipefail
: "${LAB_NAMESPACE:?set LAB_NAMESPACE}"
: "${SERVED_MODEL_NAME:?set SERVED_MODEL_NAME}"
mkdir -p artifacts
local_port="${LOCAL_PORT:-18029}"
if [[ ! "$local_port" =~ ^[0-9]+$ ]] ||
  (( local_port < 1024 || local_port > 65535 )); then
  printf 'LOCAL_PORT must be an integer from 1024 through 65535\n' >&2
  exit 2
fi

python3 - requests/completion.json artifacts/request.rendered.json \
  "$SERVED_MODEL_NAME" <<'PY'
import json
import sys
from pathlib import Path

source, output, model = sys.argv[1:]
document = json.loads(Path(source).read_text())
document["model"] = model
Path(output).write_text(json.dumps(document, indent=2) + "\n")
PY

kubectl -n "$LAB_NAMESPACE" port-forward --address 127.0.0.1 \
  service/vllm-pp-api "${local_port}:80" \
  >artifacts/port-forward.log 2>&1 &
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
curl --fail --silent --show-error \
  "http://127.0.0.1:${local_port}/v1/models" \
  >artifacts/models.json
curl --fail --silent --show-error \
  -H 'Content-Type: application/json' \
  --data-binary @artifacts/request.rendered.json \
  "http://127.0.0.1:${local_port}/v1/completions" \
  >artifacts/completion-response.json
python3 - <<'PY'
import json
from pathlib import Path

d = json.loads(Path("artifacts/completion-response.json").read_text())
assert d["object"] == "text_completion"
assert d["choices"][0]["text"]
assert d["usage"]["completion_tokens"] > 0
print("completion API contract: PASS")
PY
