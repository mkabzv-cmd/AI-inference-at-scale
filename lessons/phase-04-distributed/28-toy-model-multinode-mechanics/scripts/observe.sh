#!/usr/bin/env bash
set -euo pipefail
: "${LAB_NAMESPACE:?set LAB_NAMESPACE}"
mkdir -p artifacts/logs
kubectl -n "$LAB_NAMESPACE" get pods -o wide \
  >artifacts/pod-placement.txt
kubectl -n "$LAB_NAMESPACE" get events \
  --sort-by=.metadata.creationTimestamp \
  >artifacts/events.txt
for ordinal in 0 1 2; do
  kubectl -n "$LAB_NAMESPACE" logs "toy-tp-${ordinal}" \
    >"artifacts/logs/rank-${ordinal}.log"
done
