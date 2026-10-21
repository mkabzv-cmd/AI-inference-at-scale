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
  pod="network-benchmark-${ordinal}"
  kubectl -n "$LAB_NAMESPACE" logs "$pod" \
    >"artifacts/logs/rank-${ordinal}.log"
  kubectl -n "$LAB_NAMESPACE" get pod "$pod" \
    -o jsonpath='{.status.containerStatuses[0].imageID}{"\n"}' \
    >>artifacts/image-ids.txt
done
