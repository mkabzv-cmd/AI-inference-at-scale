#!/usr/bin/env bash
set -euo pipefail

namespaces=(
  "${TRANSFORMERS_NAMESPACE:-open-models-l11}"
  "${VLLM_NAMESPACE:-open-models-l13}"
  "${SGLANG_NAMESPACE:-open-models-l14}"
  "${LLAMA_CPP_NAMESPACE:-open-models-l15}"
)
for namespace in "${namespaces[@]}"; do
  case "$namespace" in open-models-*) ;; *) echo "unsafe namespace" >&2; exit 1 ;; esac
  kubectl delete namespace "$namespace" --ignore-not-found --wait=true
done
for namespace in "${namespaces[@]}"; do
  if kubectl get namespace "$namespace" >/dev/null 2>&1; then
    echo "namespace remains: $namespace" >&2
    exit 1
  fi
done
printf 'all engine namespaces absent; restore GPU node-group desired/minimum capacity\n'
