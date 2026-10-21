#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION}"
: "${EKS_CLUSTER_NAME:?Set EKS_CLUSTER_NAME}"
: "${LAB_NAMESPACE:?Set LAB_NAMESPACE}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/assert-target.sh"
assert_safe_namespace_name
assert_kube_context_matches_cluster
assert_namespace_owned_or_absent

kubectl delete namespace "$LAB_NAMESPACE" \
  --ignore-not-found=true \
  --wait=true \
  --timeout=10m

namespace="$(
  kubectl get namespace "$LAB_NAMESPACE" \
    --ignore-not-found \
    -o name
)"
if [[ -n "$namespace" ]]; then
  printf 'Namespace still exists: %s\n' "$LAB_NAMESPACE" >&2
  exit 1
fi
printf '[ok] namespace absent: %s\n' "$LAB_NAMESPACE"
