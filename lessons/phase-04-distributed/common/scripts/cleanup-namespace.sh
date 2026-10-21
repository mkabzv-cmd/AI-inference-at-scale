#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/assert-eks-target.sh"

kubectl delete namespace "$LAB_NAMESPACE" \
  --ignore-not-found=true \
  --wait=true \
  --timeout=15m

if kubectl get namespace "$LAB_NAMESPACE" >/dev/null 2>&1; then
  printf '[fail] namespace still exists: %s\n' "$LAB_NAMESPACE" >&2
  exit 1
fi

leftovers="$(
  kubectl get all --all-namespaces \
    -l app.kubernetes.io/part-of=oms-distributed-course \
    -o custom-columns='NAMESPACE:.metadata.namespace,KIND:.kind,NAME:.metadata.name' \
    --no-headers 2>/dev/null |
    awk -v namespace="$LAB_NAMESPACE" '$1 == namespace' || true
)"
if [[ -n "$leftovers" ]]; then
  printf '[fail] lesson resources remain in %s:\n%s\n' \
    "$LAB_NAMESPACE" "$leftovers" >&2
  exit 1
fi
printf '[ok] namespace absent and no labelled resources remain for it\n'
