#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:=open-models-l15}"
: "${IMAGE_URI:?set IMAGE_URI to the pushed CUDA image@sha256 digest}"
python3 scripts/render-k8s.py
manifest=artifacts/rendered-k8s.yaml
if grep -Eq \
  '^[[:space:]]*(type:[[:space:]]*(LoadBalancer|NodePort|ExternalName)|host(Network|PID|IPC):[[:space:]]*true|externalIPs:)' \
  "$manifest"; then
  echo "refusing externally reachable or host-level networking" >&2
  exit 1
fi
kubectl create namespace "$LAB_NAMESPACE" --dry-run=client -o yaml |
  kubectl apply -f -
kubectl label namespace "$LAB_NAMESPACE" \
  app.kubernetes.io/part-of=open-model-systems-course \
  open-model-systems.io/lesson=15 --overwrite
kubectl apply --dry-run=server -f "$manifest"
kubectl apply -f "$manifest"
kubectl rollout status deployment/llama-cpp -n "$LAB_NAMESPACE" --timeout=25m
