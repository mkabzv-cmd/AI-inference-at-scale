#!/usr/bin/env bash
set -euo pipefail
: "${LAB_NAMESPACE:?set LAB_NAMESPACE}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/../../common/scripts/assert-eks-target.sh"
mkdir -p artifacts
timeline="artifacts/worker-loss-timeline.txt"
head_pod="$(
  kubectl -n "$LAB_NAMESPACE" get pod \
    -l ray.io/cluster=vllm-pp,ray.io/node-type=head \
    -o jsonpath='{.items[0].metadata.name}'
)"
[[ -n "$head_pod" ]] || {
  printf 'no Ray head Pod found\n' >&2
  exit 1
}
victim="$(
  kubectl -n "$LAB_NAMESPACE" get pod \
    -l ray.io/cluster=vllm-pp,ray.io/node-type=worker \
    --sort-by=.metadata.name \
    -o jsonpath='{.items[0].metadata.name}'
)"
[[ -n "$victim" ]] || {
  printf 'no worker Pod found\n' >&2
  exit 1
}

api_health() {
  kubectl -n "$LAB_NAMESPACE" exec "$head_pod" -- \
    python -c \
    'from urllib.request import urlopen; print(urlopen("http://127.0.0.1:8000/health", timeout=2).status)' \
    2>/dev/null || printf 'unavailable\n'
}

printf '%s victim=%s api_health=%s\n' \
  "$(date -u +%FT%TZ)" "$victim" "$(api_health)" |
  tee "$timeline"
kubectl -n "$LAB_NAMESPACE" delete pod "$victim" --wait=false
ready_workers=0
for _attempt in {1..60}; do
  state="$(
    kubectl -n "$LAB_NAMESPACE" get pods \
      -l ray.io/cluster=vllm-pp \
      -o custom-columns=NAME:.metadata.name,READY:.status.containerStatuses[0].ready,PHASE:.status.phase \
      --no-headers 2>&1 || true
  )"
  printf '%s api_health=%s\n%s\n' \
    "$(date -u +%FT%TZ)" "$(api_health)" "$state" >>"$timeline"
  ready_workers="$(
    kubectl -n "$LAB_NAMESPACE" get pods \
      -l ray.io/cluster=vllm-pp,ray.io/node-type=worker \
      -o jsonpath='{range .items[?(@.status.containerStatuses[0].ready==true)]}{.metadata.name}{"\n"}{end}' |
      wc -l | tr -d ' '
  )"
  [[ "$ready_workers" == "2" ]] && break
  sleep 10
done
printf '%s final_api_health=%s\n' \
  "$(date -u +%FT%TZ)" "$(api_health)" >>"$timeline"
if [[ "$ready_workers" != "2" ]]; then
  printf 'worker replacement did not become Ready; inspect %s\n' \
    "$timeline" >&2
  exit 1
fi
printf '%s\n' \
  'Worker replacement observed. Inspect API and restart the engine explicitly.'
