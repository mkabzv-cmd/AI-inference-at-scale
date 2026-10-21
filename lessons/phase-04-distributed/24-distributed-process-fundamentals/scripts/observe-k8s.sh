#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:?set LAB_NAMESPACE}"
mkdir -p artifacts/k8s/logs

kubectl -n "$LAB_NAMESPACE" get pods -o wide \
  >artifacts/k8s/pod-placement.txt
kubectl -n "$LAB_NAMESPACE" get events \
  --sort-by=.metadata.creationTimestamp \
  >artifacts/k8s/events.txt
kubectl -n "$LAB_NAMESPACE" get statefulset,service,endpoints -o yaml \
  >artifacts/k8s/objects.yaml
for ordinal in 0 1 2; do
  kubectl -n "$LAB_NAMESPACE" logs "collectives-${ordinal}" \
    >"artifacts/k8s/logs/rank-${ordinal}.log"
done
printf '%s\n' \
  'evidence captured; review internal node names and addresses before sharing'
