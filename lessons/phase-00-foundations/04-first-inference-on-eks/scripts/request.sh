#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION}"
: "${EKS_CLUSTER_NAME:?Set EKS_CLUSTER_NAME}"
: "${LAB_NAMESPACE:?Set LAB_NAMESPACE}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/assert-target.sh"
assert_safe_namespace_name
assert_kube_context_matches_cluster
assert_namespace_owned_or_absent

local_port="${LOCAL_PORT:-18080}"
prompt="${PROMPT:-Kubernetes schedules the model}"
mkdir -p .lab results

python3 - "$prompt" > .lab/request.json <<'PY'
import json
import sys
json.dump(
    {
        "prompt": sys.argv[1],
        "max_new_tokens": 12,
        "temperature": 0.0,
        "top_p": 1.0,
        "seed": 42,
    },
    sys.stdout,
)
PY

kubectl port-forward \
  --namespace "$LAB_NAMESPACE" \
  service/tiny-gpt2 \
  "${local_port}:80" >.lab/port-forward.log 2>&1 &
forward_pid=$!
cleanup_forward() {
  kill "$forward_pid" >/dev/null 2>&1 || true
  wait "$forward_pid" >/dev/null 2>&1 || true
}
trap cleanup_forward EXIT

ready=false
for _ in $(seq 1 30); do
  if curl --silent --fail "http://127.0.0.1:${local_port}/readyz" >/dev/null; then
    ready=true
    break
  fi
  sleep 1
done
if [[ "$ready" != "true" ]]; then
  printf 'Port-forwarded service did not become ready.\n' >&2
  cat .lab/port-forward.log >&2
  exit 1
fi

curl --silent --show-error --fail \
  "http://127.0.0.1:${local_port}/info" > results/info.json

curl --no-buffer --silent --show-error --fail \
  --header 'Content-Type: application/json' \
  --data-binary @.lab/request.json \
  "http://127.0.0.1:${local_port}/generate" \
  | tee results/response.ndjson

python3 - <<'PY'
import json
from pathlib import Path
info = json.loads(Path("results/info.json").read_text(encoding="utf-8"))
events = [
    json.loads(line)
    for line in Path("results/response.ndjson").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
assert info["ready"] is True
assert info["cuda_available"] is True
assert str(info["device"]).startswith("cuda")
assert events and events[-1]["event"] == "complete"
assert any(event["event"] == "token" for event in events)
print("[ok] ready CUDA server returned token events and a completion event")
PY
