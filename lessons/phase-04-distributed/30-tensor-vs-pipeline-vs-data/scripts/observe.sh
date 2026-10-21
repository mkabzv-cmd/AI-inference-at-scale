#!/usr/bin/env bash
set -euo pipefail
: "${LAB_NAMESPACE:?set LAB_NAMESPACE}"
: "${STRATEGY:?set STRATEGY}"
directory="artifacts/observe-${STRATEGY}"
mkdir -p "$directory"
kubectl -n "$LAB_NAMESPACE" get all,raycluster -o wide \
  >"$directory/objects.txt" 2>&1 || true
kubectl -n "$LAB_NAMESPACE" get events \
  --sort-by=.metadata.creationTimestamp >"$directory/events.txt"
kubectl -n "$LAB_NAMESPACE" get pods \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.nodeName}{"\t"}{.status.containerStatuses[0].imageID}{"\n"}{end}' \
  >"$directory/pod-node-image-map.txt"
for pod in $(kubectl -n "$LAB_NAMESPACE" get pod -o name); do
  name="${pod#pod/}"
  kubectl -n "$LAB_NAMESPACE" logs "$name" --all-containers --prefix \
    >"$directory/${name}.log" 2>&1 || true
  kubectl -n "$LAB_NAMESPACE" exec "$name" -- nvidia-smi \
    >"$directory/${name}-nvidia-smi.txt" 2>&1 || true
done
if [[ "$STRATEGY" != "data-parallel" ]]; then
  head_pod="$(
    kubectl -n "$LAB_NAMESPACE" get pod \
      -l ray.io/node-type=head -o jsonpath='{.items[0].metadata.name}'
  )"
  kubectl -n "$LAB_NAMESPACE" exec "$head_pod" -- ray status \
    >"$directory/ray-status.txt"
  kubectl -n "$LAB_NAMESPACE" exec "$head_pod" -- \
    cat /tmp/vllm-server.log >"$directory/vllm-server.log"
fi
