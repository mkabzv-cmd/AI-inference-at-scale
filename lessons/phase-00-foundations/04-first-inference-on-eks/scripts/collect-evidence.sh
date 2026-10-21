#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:?Set LAB_NAMESPACE}"
: "${GPU_NODEGROUP_NAME:?Set GPU_NODEGROUP_NAME}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/assert-target.sh"
assert_safe_namespace_name
assert_kube_context_matches_cluster
assert_namespace_owned_or_absent

mkdir -p results

kubectl get deployment,pod,service,endpointslice \
  --namespace "$LAB_NAMESPACE" \
  -o wide > results/kubernetes-objects.txt
kubectl describe deployment tiny-gpt2 \
  --namespace "$LAB_NAMESPACE" > results/deployment-describe.txt
kubectl describe pod \
  --namespace "$LAB_NAMESPACE" \
  -l app.kubernetes.io/name=tiny-gpt2 > results/pod-describe.txt
kubectl logs \
  --namespace "$LAB_NAMESPACE" \
  -l app.kubernetes.io/name=tiny-gpt2 \
  --tail=500 > results/server.log
kubectl get events \
  --namespace "$LAB_NAMESPACE" \
  --sort-by=.lastTimestamp > results/events.txt
kubectl get nodes \
  -l "eks.amazonaws.com/nodegroup=$GPU_NODEGROUP_NAME" \
  -o wide > results/gpu-nodes.txt

printf 'Evidence saved under results/. Review for private metadata before sharing.\n'
