#!/usr/bin/env bash
set -euo pipefail
: "${LAB_NAMESPACE:?set LAB_NAMESPACE}"
mkdir -p artifacts
head_pod="$(
  kubectl -n "$LAB_NAMESPACE" get pod \
    -l ray.io/cluster=vllm-pp,ray.io/node-type=head \
    -o jsonpath='{.items[0].metadata.name}'
)"
kubectl -n "$LAB_NAMESPACE" get raycluster,pods,service,endpoints -o wide \
  >artifacts/kubernetes-placement.txt
kubectl -n "$LAB_NAMESPACE" get events \
  --sort-by=.metadata.creationTimestamp \
  >artifacts/events.txt
kubectl -n "$LAB_NAMESPACE" exec "$head_pod" -- ray status \
  >artifacts/ray-status.txt
kubectl -n "$LAB_NAMESPACE" exec "$head_pod" -- \
  cat /tmp/vllm-server.log >artifacts/vllm-server.log
for pod in $(
  kubectl -n "$LAB_NAMESPACE" get pod \
    -l ray.io/cluster=vllm-pp -o name
); do
  name="${pod#pod/}"
  kubectl -n "$LAB_NAMESPACE" exec "$name" -- \
    cat /models/.model-provenance.json \
    >"artifacts/${name}-model-provenance.json"
  kubectl -n "$LAB_NAMESPACE" exec "$name" -- nvidia-smi \
    >"artifacts/${name}-nvidia-smi.txt"
done
kubectl -n "$LAB_NAMESPACE" get pod \
  -l ray.io/cluster=vllm-pp \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.nodeName}{"\t"}{.status.containerStatuses[0].imageID}{"\n"}{end}' \
  >artifacts/image-and-node-map.txt
