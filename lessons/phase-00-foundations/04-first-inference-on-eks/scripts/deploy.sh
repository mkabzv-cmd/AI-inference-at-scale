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

if [[ ! -f .lab/workload.yaml ]]; then
  printf 'Missing .lab/workload.yaml; render manifests first.\n' >&2
  exit 2
fi

kubectl apply --server-side=false -f .lab/workload.yaml
kubectl rollout status \
  deployment/tiny-gpt2 \
  --namespace "$LAB_NAMESPACE" \
  --timeout=12m
kubectl get deployment,pod,service \
  --namespace "$LAB_NAMESPACE" \
  -o wide
