#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:=open-models-l14}"
# shellcheck disable=SC1091
source artifacts/image.env
export IMAGE_URI
python3 scripts/render.py
manifest=artifacts/rendered.yaml
grep -q 'type: ClusterIP' "$manifest"
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
  open-model-systems.io/lesson=14 --overwrite
kubectl apply --dry-run=server -f "$manifest"
kubectl apply -f "$manifest"
kubectl rollout status deployment/sglang -n "$LAB_NAMESPACE" --timeout=25m
