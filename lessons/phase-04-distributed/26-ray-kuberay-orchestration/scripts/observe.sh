#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:?set LAB_NAMESPACE}"
mkdir -p artifacts
head_pod="$(
  kubectl -n "$LAB_NAMESPACE" get pod \
    -l ray.io/cluster=teaching-ray,ray.io/node-type=head \
    -o jsonpath='{.items[0].metadata.name}'
)"
kubectl -n "$LAB_NAMESPACE" get raycluster,pods,services -o wide \
  >artifacts/kubernetes-placement.txt
kubectl -n "$LAB_NAMESPACE" get raycluster teaching-ray -o yaml \
  >artifacts/raycluster.yaml
kubectl -n "$LAB_NAMESPACE" get events \
  --sort-by=.metadata.creationTimestamp \
  >artifacts/events.txt
kubectl -n "$LAB_NAMESPACE" exec "$head_pod" -- ray status \
  >artifacts/ray-status.txt
kubectl -n "$LAB_NAMESPACE" logs \
  -l ray.io/node-type=worker --prefix --tail=500 \
  >artifacts/worker-logs.txt
printf 'Ray/Kubernetes evidence saved under artifacts/\n'
