#!/usr/bin/env bash
set -euo pipefail

required_vars=(AWS_REGION EKS_CLUSTER_NAME GPU_NODEGROUP_NAME LAB_NAMESPACE)
for name in "${required_vars[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    printf 'Required environment variable is unset: %s\n' "$name" >&2
    exit 2
  fi
done
for command_name in aws kubectl; do
  command -v "$command_name" >/dev/null 2>&1 || {
    printf 'Required command not found: %s\n' "$command_name" >&2
    exit 2
  }
done

expected_endpoint="$(
  aws eks describe-cluster \
    --region "$AWS_REGION" \
    --name "$EKS_CLUSTER_NAME" \
    --query 'cluster.endpoint' \
    --output text
)"
current_endpoint="$(
  kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}'
)"
if [[ "$current_endpoint" != "$expected_endpoint" ]]; then
  printf '[fail] kubectl context does not target the named EKS cluster\n' >&2
  exit 1
fi

read -r desired minimum < <(
  aws eks describe-nodegroup \
    --region "$AWS_REGION" \
    --cluster-name "$EKS_CLUSTER_NAME" \
    --nodegroup-name "$GPU_NODEGROUP_NAME" \
    --query 'nodegroup.[scalingConfig.desiredSize,scalingConfig.minSize]' \
    --output text
)

failures=0
if [[ "$desired" == "0" ]]; then
  printf '[ok] managed node-group desired capacity is zero\n'
else
  printf '[fail] managed node-group desired capacity is %s, expected 0\n' "$desired"
  failures=$((failures + 1))
fi
if [[ "$minimum" == "0" ]]; then
  printf '[ok] managed node-group minimum capacity is zero\n'
else
  printf '[fail] managed node-group minimum capacity is %s, expected 0\n' "$minimum"
  failures=$((failures + 1))
fi

namespace="$(
  kubectl get namespace "$LAB_NAMESPACE" \
    --ignore-not-found \
    -o name
)"
if [[ -n "$namespace" ]]; then
  printf '[fail] namespace still exists: %s\n' "$LAB_NAMESPACE"
  failures=$((failures + 1))
else
  printf '[ok] namespace is absent: %s\n' "$LAB_NAMESPACE"
fi

nodes="$(
  kubectl get nodes \
    -l "eks.amazonaws.com/nodegroup=$GPU_NODEGROUP_NAME" \
    -o name
)"
if [[ -n "$nodes" ]]; then
  printf '[fail] node objects still remain for the managed GPU group:\n%s\n' \
    "$nodes"
  failures=$((failures + 1))
else
  printf '[ok] no node object remains for the managed GPU group\n'
fi

if (( failures > 0 )); then
  printf 'Cloud cleanup verification failed with %d problem(s).\n' "$failures"
  exit 1
fi
printf 'Cloud cleanup verification passed.\n'
