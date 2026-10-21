#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:?set LAB_NAMESPACE}"
: "${STRATEGY:?set STRATEGY}"
: "${SERVED_MODEL_NAME:?set SERVED_MODEL_NAME}"
: "${MAX_MODEL_LEN:?set MAX_MODEL_LEN}"
: "${MAX_NUM_SEQS:?set MAX_NUM_SEQS}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/../../common/scripts/assert-eks-target.sh"
case "$STRATEGY" in
  tensor-parallel)
    tp=3
    pp=1
    ;;
  pipeline-parallel)
    tp=1
    pp=3
    ;;
  *)
    printf 'start-ray-server requires tensor-parallel or pipeline-parallel\n' >&2
    exit 2
    ;;
esac
head_pod="$(
  kubectl -n "$LAB_NAMESPACE" get pod \
    -l ray.io/cluster=comparison-ray,ray.io/node-type=head \
    -o jsonpath='{.items[0].metadata.name}'
)"
gpus="$(
  kubectl -n "$LAB_NAMESPACE" exec "$head_pod" -- \
  python -c \
  'import ray; ray.init(address="auto"); print(int(ray.cluster_resources().get("GPU", 0)))'
)"
[[ "$gpus" == "3" ]] || {
  printf 'expected 3 Ray GPUs; found %s\n' "$gpus" >&2
  exit 1
}
kubectl -n "$LAB_NAMESPACE" exec "$head_pod" -- \
  /bin/bash -ec '
    served_model_name="$1"
    tp="$2"
    pp="$3"
    max_model_len="$4"
    max_num_seqs="$5"
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
    nohup vllm serve /models/snapshot \
      --served-model-name "$served_model_name" \
      --host 0.0.0.0 --port 8000 \
      --tensor-parallel-size "$tp" \
      --pipeline-parallel-size "$pp" \
      --distributed-executor-backend ray \
      --max-model-len "$max_model_len" \
      --max-num-seqs "$max_num_seqs" \
      >/tmp/vllm-server.log 2>&1 &
    echo "$!" >/tmp/vllm-server.pid
  ' lesson-30-vllm \
  "$SERVED_MODEL_NAME" \
  "$tp" \
  "$pp" \
  "$MAX_MODEL_LEN" \
  "$MAX_NUM_SEQS"
for _attempt in {1..120}; do
  if kubectl -n "$LAB_NAMESPACE" exec "$head_pod" -- \
    python -c \
    'from urllib.request import urlopen; urlopen("http://127.0.0.1:8000/health", timeout=2)' \
    >/dev/null 2>&1; then
    printf '[ok] %s server ready (TP=%s PP=%s)\n' "$STRATEGY" "$tp" "$pp"
    exit 0
  fi
  sleep 5
done
kubectl -n "$LAB_NAMESPACE" exec "$head_pod" -- \
  tail -200 /tmp/vllm-server.log >&2 || true
exit 1
