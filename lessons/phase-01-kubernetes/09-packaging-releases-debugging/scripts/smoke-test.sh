#!/usr/bin/env bash
set -euo pipefail

namespace="${LAB_NAMESPACE:-packaging-lab}"
release="${HELM_RELEASE:-course}"
local_port="${LOCAL_PORT:-18080}"

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

for _attempt in {1..30}; do
  if curl --fail --silent \
    "http://127.0.0.1:${local_port}/health/ready" >/dev/null; then
    break
  fi
  sleep 1
done
curl --fail --silent --show-error \
  "http://127.0.0.1:${local_port}/health/ready" >/dev/null

response="$(
  curl --fail --silent --show-error \
    "http://127.0.0.1:${local_port}/"
)"
printf '%s\n' "$response" | tee artifacts/smoke-response.json
RESPONSE="$response" python3 - <<'PY'
import json
import os

response = json.loads(os.environ["RESPONSE"])
for key in ("message", "version", "fault_mode"):
    if key not in response:
        raise SystemExit(f"response is missing {key!r}")

expected_message = os.environ.get("EXPECTED_MESSAGE")
expected_version = os.environ.get("EXPECTED_VERSION")
if expected_message is not None and response["message"] != expected_message:
    raise SystemExit(
        f"message mismatch: expected {expected_message!r}, "
        f"received {response['message']!r}"
    )
if expected_version is not None and response["version"] != expected_version:
    raise SystemExit(
        f"version mismatch: expected {expected_version!r}, "
        f"received {response['version']!r}"
    )
PY
printf 'behavioral smoke test: PASS\n'
