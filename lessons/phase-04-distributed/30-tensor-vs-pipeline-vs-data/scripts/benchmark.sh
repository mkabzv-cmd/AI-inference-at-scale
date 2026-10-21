#!/usr/bin/env bash
set -euo pipefail
: "${LAB_NAMESPACE:?set LAB_NAMESPACE}"
: "${STRATEGY:?set STRATEGY}"
: "${MODEL_ID:?set MODEL_ID}"
: "${MODEL_REVISION:?set MODEL_REVISION}"
: "${SERVED_MODEL_NAME:?set SERVED_MODEL_NAME}"
: "${VLLM_IMAGE:?set VLLM_IMAGE}"
: "${VLLM_EXPECTED_VERSION:?set VLLM_EXPECTED_VERSION}"
: "${RAY_EXPECTED_VERSION:?set RAY_EXPECTED_VERSION}"
mkdir -p artifacts

python3 - "$SERVED_MODEL_NAME" <<'PY'
import json
import sys
from pathlib import Path
d = json.loads(Path("requests/completion.json").read_text())
d["model"] = sys.argv[1]
Path("artifacts/request.rendered.json").write_text(json.dumps(d) + "\n")
PY
local_port="${LOCAL_PORT:-18030}"
if [[ ! "$local_port" =~ ^[0-9]+$ ]] ||
  (( local_port < 1024 || local_port > 65535 )); then
  printf 'LOCAL_PORT must be an integer from 1024 through 65535\n' >&2
  exit 2
fi
kubectl -n "$LAB_NAMESPACE" port-forward --address 127.0.0.1 \
  service/comparison-api "${local_port}:80" \
  >artifacts/port-forward.log 2>&1 &
forward_pid=$!
stop_forward() {
  kill "$forward_pid" >/dev/null 2>&1 || true
  wait "$forward_pid" >/dev/null 2>&1 || true
}
trap stop_forward EXIT
healthy=false
for _attempt in {1..60}; do
  if curl --silent --fail "http://127.0.0.1:${local_port}/health" \
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
if [[ "$STRATEGY" == "data-parallel" ]]; then
  runtime_pod="$(
    kubectl -n "$LAB_NAMESPACE" get pod \
      -l app.kubernetes.io/name=comparison-dp \
      -o jsonpath='{.items[0].metadata.name}'
  )"
else
  runtime_pod="$(
    kubectl -n "$LAB_NAMESPACE" get pod \
      -l ray.io/cluster=comparison-ray,ray.io/node-type=head \
      -o jsonpath='{.items[0].metadata.name}'
  )"
fi
observed_versions="$(
  kubectl -n "$LAB_NAMESPACE" exec "$runtime_pod" -- \
    python -c \
    'from importlib.metadata import version; print(version("vllm") + "\t" + version("ray"))'
)"
IFS=$'\t' read -r observed_vllm observed_ray <<<"$observed_versions"
if [[ "$observed_vllm" != "$VLLM_EXPECTED_VERSION" ||
  "$observed_ray" != "$RAY_EXPECTED_VERSION" ]]; then
  printf 'live versions differ: vLLM=%s Ray=%s; expected vLLM=%s Ray=%s\n' \
    "$observed_vllm" "$observed_ray" \
    "$VLLM_EXPECTED_VERSION" "$RAY_EXPECTED_VERSION" >&2
  exit 1
fi
python3 src/benchmark_client.py \
  --strategy "$STRATEGY" \
  --url "http://127.0.0.1:${local_port}/v1/completions" \
  --request artifacts/request.rendered.json \
  --requests "${BENCHMARK_REQUESTS:-12}" \
  --concurrency "${BENCHMARK_CONCURRENCY:-3}" \
  --model-id "$MODEL_ID" \
  --model-revision "$MODEL_REVISION" \
  --image-digest "${VLLM_IMAGE##*@}" \
  --vllm-version "$observed_vllm" \
  --ray-version "$observed_ray" \
  --output artifacts/latest-result.json
