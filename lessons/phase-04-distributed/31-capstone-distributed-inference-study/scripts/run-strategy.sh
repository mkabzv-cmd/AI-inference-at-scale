#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 1 ]]; then
  printf 'usage: %s data-parallel|tensor-parallel|pipeline-parallel\n' "$0" >&2
  exit 2
fi
strategy="$1"
case "$strategy" in
  data-parallel)
    short=dp
    ;;
  tensor-parallel)
    short=tp
    ;;
  pipeline-parallel)
    short=pp
    ;;
  *)
    printf 'unknown strategy: %s\n' "$strategy" >&2
    exit 2
    ;;
esac
: "${RUN_REPETITION:?set RUN_REPETITION}"
: "${STUDY_ID:?set STUDY_ID}"
: "${MODEL_ID:?set MODEL_ID}"
: "${MODEL_REVISION:?set MODEL_REVISION}"
: "${SERVED_MODEL_NAME:?set SERVED_MODEL_NAME}"
: "${VLLM_IMAGE:?set VLLM_IMAGE}"
: "${GPU_NODEGROUP:?set GPU_NODEGROUP}"
: "${VLLM_EXPECTED_VERSION:?set VLLM_EXPECTED_VERSION}"
: "${RAY_EXPECTED_VERSION:?set RAY_EXPECTED_VERSION}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
lesson_dir="$(cd "$script_dir/.." && pwd)"
layout_dir="$(cd "$lesson_dir/../30-tensor-vs-pipeline-vs-data" && pwd)"
common_dir="$(cd "$lesson_dir/../common/scripts" && pwd)"
spec="$lesson_dir/artifacts/study-spec.json"
[[ -f "$spec" ]] || {
  printf 'missing %s; create and validate the study spec first\n' "$spec" >&2
  exit 2
}
python3 - \
  "$spec" \
  "$lesson_dir/workloads/completions.ndjson" \
  "$strategy" \
  "$RUN_REPETITION" \
  "$STUDY_ID" \
  "$MODEL_ID" \
  "$MODEL_REVISION" \
  "$SERVED_MODEL_NAME" \
  "$VLLM_IMAGE" \
  "$VLLM_EXPECTED_VERSION" \
  "$RAY_EXPECTED_VERSION" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

(
    spec_path,
    workload_path,
    strategy,
    repetition_value,
    study_id,
    model_id,
    model_revision,
    served_name,
    image,
    vllm_version,
    ray_version,
) = sys.argv[1:]
spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
expected = {
    "study ID": (study_id, spec["study_id"]),
    "model ID": (model_id, spec["model"]["id"]),
    "model revision": (model_revision, spec["model"]["revision"]),
    "served model": (served_name, spec["model"]["served_name"]),
    "image": (image, spec["software"]["image"]),
    "vLLM version": (
        vllm_version,
        spec["software"]["vllm_expected_version"],
    ),
    "Ray version": (ray_version, spec["software"]["ray_expected_version"]),
}
for label, (actual, frozen) in expected.items():
    if actual != frozen:
        raise SystemExit(
            f"{label} differs from frozen study: {actual!r} != {frozen!r}"
        )
try:
    repetition = int(repetition_value)
except ValueError as error:
    raise SystemExit("RUN_REPETITION must be an integer") from error
if not 1 <= repetition <= int(spec["design"]["repeats"]):
    raise SystemExit("RUN_REPETITION is outside the frozen study")
if strategy not in spec["design"]["strategies"]:
    raise SystemExit("strategy is absent from the frozen study")
workload_hash = hashlib.sha256(Path(workload_path).read_bytes()).hexdigest()
if workload_hash != spec["workload"]["sha256"]:
    raise SystemExit("workload bytes differ from the frozen study")
print("frozen study inputs: PASS")
PY

export STRATEGY="$strategy"
export LAB_NAMESPACE="oms-distributed-31-${short}-${RUN_REPETITION}"
requested_cache="${MODEL_CACHE_GIB:-}"
requested_model_len="${MAX_MODEL_LEN:-}"
requested_num_seqs="${MAX_NUM_SEQS:-}"
read -r frozen_cache frozen_model_len frozen_num_seqs < <(
  python3 - "$spec" <<'PY'
import json
import sys
from pathlib import Path

spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
runtime = spec["runtime"]
print(
    runtime["model_cache_gib_per_node"],
    runtime["max_model_len"],
    runtime["max_num_seqs"],
)
PY
)
for label_and_values in \
  "MODEL_CACHE_GIB:$requested_cache:$frozen_cache" \
  "MAX_MODEL_LEN:$requested_model_len:$frozen_model_len" \
  "MAX_NUM_SEQS:$requested_num_seqs:$frozen_num_seqs"; do
  IFS=: read -r label requested frozen <<<"$label_and_values"
  if [[ -n "$requested" && "$requested" != "$frozen" ]]; then
    printf '%s=%s differs from frozen study value %s\n' \
      "$label" "$requested" "$frozen" >&2
    exit 1
  fi
done
export MODEL_CACHE_GIB="$frozen_cache"
export MAX_MODEL_LEN="$frozen_model_len"
export MAX_NUM_SEQS="$frozen_num_seqs"

cleanup_namespace() {
  (
    cd "$lesson_dir"
    "$common_dir/cleanup-namespace.sh"
  ) || true
}
trap cleanup_namespace EXIT

(
  cd "$layout_dir"
  ./scripts/render.py
  ./scripts/deploy-strategy.sh
  if [[ "$strategy" != "data-parallel" ]]; then
    ./scripts/start-ray-server.sh
  fi
)

if [[ "$strategy" == "data-parallel" ]]; then
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

mkdir -p \
  "$lesson_dir/artifacts/runs" \
  "$lesson_dir/artifacts/evidence/${strategy}-${RUN_REPETITION}"
local_port="$((18100 + RUN_REPETITION))"
kubectl -n "$LAB_NAMESPACE" port-forward --address 127.0.0.1 \
  service/comparison-api "${local_port}:80" \
  >"$lesson_dir/artifacts/evidence/${strategy}-${RUN_REPETITION}/port-forward.log" \
  2>&1 &
forward_pid=$!
stop_forward() {
  kill "$forward_pid" >/dev/null 2>&1 || true
  wait "$forward_pid" >/dev/null 2>&1 || true
}
trap 'stop_forward; cleanup_namespace' EXIT
healthy=false
for _attempt in {1..90}; do
  if curl --silent --fail "http://127.0.0.1:${local_port}/health" \
    >/dev/null 2>&1; then
    healthy=true
    break
  fi
  sleep 2
done
if [[ "$healthy" != "true" ]]; then
  printf 'port-forwarded %s API did not become healthy\n' "$strategy" >&2
  exit 1
fi

python3 "$lesson_dir/src/workload_runner.py" \
  --spec "$spec" \
  --workload "$lesson_dir/workloads/completions.ndjson" \
  --url "http://127.0.0.1:${local_port}/v1/completions" \
  --strategy "$strategy" \
  --repetition "$RUN_REPETITION" \
  --vllm-version "$observed_vllm" \
  --ray-version "$observed_ray" \
  --output \
  "$lesson_dir/artifacts/runs/${strategy}-${RUN_REPETITION}.json"

(
  cd "$layout_dir"
  ./scripts/observe.sh
  cp -R "artifacts/observe-${strategy}/." \
    "$lesson_dir/artifacts/evidence/${strategy}-${RUN_REPETITION}/"
)
stop_forward
cleanup_namespace
trap - EXIT
printf 'completed %s repetition %s\n' "$strategy" "$RUN_REPETITION"
