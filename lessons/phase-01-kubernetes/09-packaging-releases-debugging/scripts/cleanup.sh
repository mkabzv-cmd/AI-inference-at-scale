#!/usr/bin/env bash
set -euo pipefail

namespace="${LAB_NAMESPACE:-packaging-lab}"
release="${HELM_RELEASE:-course}"

helm uninstall "$release" --namespace "$namespace" 2>/dev/null || true
kubectl delete namespace "$namespace" --ignore-not-found --wait=true

if kubectl get namespace "$namespace" >/dev/null 2>&1; then
  printf 'namespace still exists: %s\n' "$namespace" >&2
  exit 1
fi
printf 'release and namespace removed\n'
