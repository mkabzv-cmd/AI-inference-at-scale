#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:?set LAB_NAMESPACE}"
: "${SERVED_MODEL_NAME:?set SERVED_MODEL_NAME}"
: "${MAX_MODEL_LEN:?set MAX_MODEL_LEN}"
: "${MAX_NUM_SEQS:?set MAX_NUM_SEQS}"
: "${VLLM_EXPECTED_VERSION:?set VLLM_EXPECTED_VERSION}"
: "${RAY_EXPECTED_VERSION:?set RAY_EXPECTED_VERSION}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/../../common/scripts/assert-eks-target.sh"
head_pod="$(
  kubectl -n "$LAB_NAMESPACE" get pod \
    -l ray.io/cluster=vllm-pp,ray.io/node-type=head \
    -o jsonpath='{.items[0].metadata.name}'
)"
observed_versions="$(
  kubectl -n "$LAB_NAMESPACE" exec "$head_pod" -- \
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
mkdir -p artifacts
printf 'vllm=%s\nray=%s\n' "$observed_vllm" "$observed_ray" \
  >artifacts/live-package-versions.txt

ray_gpus="$(
  kubectl -n "$LAB_NAMESPACE" exec "$head_pod" -- \
    python -c \
    'import ray; ray.init(address="auto"); print(int(ray.cluster_resources().get("GPU", 0)))'
)"
if [[ "$ray_gpus" != "3" ]]; then
  printf 'expected exactly 3 Ray GPUs, found %s\n' "$ray_gpus" >&2
  exit 1
fi

quantization_args=()
if [[ -n "${QUANTIZATION:-}" ]]; then
  quantization_args=(--quantization "$QUANTIZATION")
fi
printf '%q ' \
  vllm serve /models/snapshot \
  --served-model-name "$SERVED_MODEL_NAME" \
  --tensor-parallel-size 1 \
  --pipeline-parallel-size 3 \
  --distributed-executor-backend ray \
  --max-model-len "$MAX_MODEL_LEN" \
  --max-num-seqs "$MAX_NUM_SEQS" \
  "${quantization_args[@]}" \
  >artifacts/vllm-launch-command.txt
printf '\n' >>artifacts/vllm-launch-command.txt

kubectl -n "$LAB_NAMESPACE" exec "$head_pod" -- \
  /bin/bash -ec '
    served_model_name="$1"
    max_model_len="$2"
    max_num_seqs="$3"
    quantization="$4"
    if [[ -s /tmp/vllm-server.pid ]]; then
      old_pid="$(cat /tmp/vllm-server.pid)"
      if [[ "$old_pid" =~ ^[0-9]+$ ]] && kill -0 "$old_pid" 2>/dev/null; then
        kill "$old_pid"
        for _stop_attempt in {1..30}; do
          kill -0 "$old_pid" 2>/dev/null || break
          sleep 1
        done
        kill -0 "$old_pid" 2>/dev/null && kill -KILL "$old_pid"
      fi
      rm -f /tmp/vllm-server.pid
    fi
    args=(
      vllm serve /models/snapshot
      --served-model-name "$served_model_name"
      --tensor-parallel-size 1
      --pipeline-parallel-size 3
      --distributed-executor-backend ray
      --host 0.0.0.0
      --port 8000
      --max-model-len "$max_model_len"
      --max-num-seqs "$max_num_seqs"
    )
    [[ -n "$quantization" ]] &&
      args+=(--quantization "$quantization")
    nohup "${args[@]}" >/tmp/vllm-server.log 2>&1 &
    echo "$!" >/tmp/vllm-server.pid
  ' lesson-29-vllm \
  "$SERVED_MODEL_NAME" \
  "$MAX_MODEL_LEN" \
  "$MAX_NUM_SEQS" \
  "${QUANTIZATION:-}"

for _attempt in {1..120}; do
  if kubectl -n "$LAB_NAMESPACE" exec "$head_pod" -- \
    python -c \
    'from urllib.request import urlopen; urlopen("http://127.0.0.1:8000/health", timeout=2)' \
    >/dev/null 2>&1; then
    printf '[ok] vLLM health endpoint ready\n'
    exit 0
  fi
  sleep 5
done
kubectl -n "$LAB_NAMESPACE" exec "$head_pod" -- \
  tail -200 /tmp/vllm-server.log >&2 || true
exit 1
