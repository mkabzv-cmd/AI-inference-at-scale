#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:?set LAB_NAMESPACE for the currently deployed layout}"
: "${FAILURE_STRATEGY:?set FAILURE_STRATEGY}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/../../common/scripts/assert-eks-target.sh"
case "$FAILURE_STRATEGY" in
  data-parallel)
    selector='app.kubernetes.io/name=comparison-dp'
    ;;
  tensor-parallel | pipeline-parallel)
    selector='ray.io/cluster=comparison-ray,ray.io/node-type=worker'
    ;;
  *)
    printf 'invalid FAILURE_STRATEGY\n' >&2
    exit 2
    ;;
esac

mkdir -p artifacts/failure
timeline="artifacts/failure/timeline.ndjson"
: >"$timeline"

emit() {
  local event="$1"
  local detail="$2"
  python3 - "$timeline" "$event" "$FAILURE_STRATEGY" "$detail" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path, event, strategy, detail = sys.argv[1:]
record = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "event": event,
    "strategy": strategy,
    "detail": detail,
}
with Path(path).open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(record, sort_keys=True) + "\n")
PY
}

victim="$(
  kubectl -n "$LAB_NAMESPACE" get pods \
    -l "$selector" --sort-by=.metadata.name \
    -o jsonpath='{.items[0].metadata.name}'
)"
[[ -n "$victim" ]] || {
  printf 'no participant Pod found for selector %s\n' "$selector" >&2
  exit 1
}

if [[ "$FAILURE_STRATEGY" == "data-parallel" ]]; then
  probe_pod="$(
    kubectl -n "$LAB_NAMESPACE" get pods \
      -l "$selector" --sort-by=.metadata.name \
      -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' |
      awk -v victim="$victim" '$0 != victim {print; exit}'
  )"
else
  probe_pod="$(
    kubectl -n "$LAB_NAMESPACE" get pod \
      -l ray.io/cluster=comparison-ray,ray.io/node-type=head \
      -o jsonpath='{.items[0].metadata.name}'
  )"
fi
[[ -n "$probe_pod" ]] || {
  printf 'no surviving API probe Pod found\n' >&2
  exit 1
}

api_health() {
  kubectl -n "$LAB_NAMESPACE" exec "$probe_pod" -- \
    python -c \
    'from urllib.request import urlopen; print(urlopen("http://comparison-api/health", timeout=2).status)' \
    2>/dev/null || printf 'unavailable\n'
}

baseline="$(
  kubectl -n "$LAB_NAMESPACE" get pods -o wide --no-headers |
    tr '\n' ';'
)"
emit baseline "$baseline"
emit baseline_api_health "$(api_health)"
emit participant_selected "$victim"
kubectl -n "$LAB_NAMESPACE" delete pod "$victim" --wait=false
emit participant_deleted "$victim"

for attempt in {1..24}; do
  state="$(
    kubectl -n "$LAB_NAMESPACE" get pods \
      -o custom-columns=NAME:.metadata.name,READY:.status.containerStatuses[0].ready,PHASE:.status.phase \
      --no-headers 2>&1 |
      tr '\n' ';'
  )"
  emit observed \
    "attempt=${attempt};api_health=$(api_health);pods=${state}"
  sleep 5
done
printf 'timeline written to %s; test/restart the API and append recovery evidence\n' \
  "$timeline"
