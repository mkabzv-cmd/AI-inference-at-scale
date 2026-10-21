#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:=open-models-l11}"
if [[ ! "$LAB_NAMESPACE" =~ ^open-models-[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] ||
  (( ${#LAB_NAMESPACE} > 63 )); then
  echo "refusing unexpected namespace" >&2
  exit 1
fi
if kubectl get namespace "$LAB_NAMESPACE" >/dev/null 2>&1; then
  owner="$(
    kubectl get namespace "$LAB_NAMESPACE" \
      -o jsonpath='{.metadata.labels.app\.kubernetes\.io/part-of}'
  )"
  lesson="$(
    kubectl get namespace "$LAB_NAMESPACE" \
      -o jsonpath='{.metadata.labels.open-model-systems\.io/lesson}'
  )"
  [[ "$owner" == "open-model-systems-course" && "$lesson" == "11" ]] || {
    echo "refusing to delete a namespace without lesson-11 ownership labels" >&2
    exit 1
  }
fi

kubectl delete namespace "$LAB_NAMESPACE" --ignore-not-found --wait=true
if kubectl get namespace "$LAB_NAMESPACE" >/dev/null 2>&1; then
  echo "namespace still exists" >&2
  exit 1
fi
printf 'namespace %s is absent; restore GPU node-group capacity separately\n' \
  "$LAB_NAMESPACE"
