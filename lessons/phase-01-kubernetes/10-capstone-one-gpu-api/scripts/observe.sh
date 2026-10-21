#!/usr/bin/env bash
set -euo pipefail

namespace="${LAB_NAMESPACE:-one-gpu-api}"
release="${HELM_RELEASE:-one-gpu}"
mkdir -p artifacts

pod="$(
  kubectl -n "$namespace" get pods \
    -l "app.kubernetes.io/instance=${release}" \
    --sort-by=.metadata.creationTimestamp \
    -o jsonpath='{.items[-1:].metadata.name}'
)"
if [[ -z "$pod" ]]; then
  printf 'no Pod found for Helm release %s\n' "$release" >&2
  exit 1
fi

kubectl -n "$namespace" get all,pvc -o wide \
  >artifacts/kubernetes-objects.txt
kubectl -n "$namespace" get events \
  --sort-by=.metadata.creationTimestamp \
  >artifacts/events.txt
kubectl -n "$namespace" logs "$pod" -c download-model \
  >artifacts/downloader.log
kubectl -n "$namespace" logs "$pod" -c api \
  >artifacts/api.log
kubectl -n "$namespace" exec "$pod" -c api -- nvidia-smi \
  >artifacts/nvidia-smi.txt
kubectl -n "$namespace" get pod "$pod" -o yaml \
  >artifacts/pod.yaml
helm get values "$release" -n "$namespace" --all \
  >artifacts/helm-values.yaml
helm get manifest "$release" -n "$namespace" \
  >artifacts/helm-manifest.yaml
printf 'observation bundle written to artifacts/\n'
