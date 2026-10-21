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

printf '== Managed node group ==\n'
printf 'status\tdesired\tmin\tmax\tinstance-types\n'
aws eks describe-nodegroup \
  --region "$AWS_REGION" \
  --cluster-name "$EKS_CLUSTER_NAME" \
  --nodegroup-name "$GPU_NODEGROUP_NAME" \
  --query 'nodegroup.[status,scalingConfig.desiredSize,scalingConfig.minSize,scalingConfig.maxSize,join(`,`,instanceTypes)]' \
  --output text

expected_endpoint="$(
  aws eks describe-cluster \
    --region "$AWS_REGION" \
    --name "$EKS_CLUSTER_NAME" \
    --query 'cluster.endpoint' \
    --output text
)"
current_context="$(kubectl config current-context)"
current_endpoint="$(
  kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}'
)"
if [[ "$current_endpoint" != "$expected_endpoint" ]]; then
  printf 'Refusing to audit an unexpected Kubernetes context.\n' >&2
  printf 'current context: %s\n' "$current_context" >&2
  printf 'current endpoint: %s\n' "$current_endpoint" >&2
  printf 'expected EKS endpoint: %s\n' "$expected_endpoint" >&2
  exit 1
fi
printf 'kubectl context matches EKS cluster: %s\n' "$current_context"

printf '\n== Lesson namespace ==\n'
namespace="$(
  kubectl get namespace "$LAB_NAMESPACE" \
    --ignore-not-found \
    -o name
)"
if [[ -n "$namespace" ]]; then
  kubectl get namespace "$LAB_NAMESPACE" -o wide
else
  printf 'namespace/%s not found\n' "$LAB_NAMESPACE"
fi

printf '\n== Potentially billable Kubernetes objects across all namespaces ==\n'
load_balancers="$(
  kubectl get service --all-namespaces \
    -o custom-columns='NAMESPACE:.metadata.namespace,NAME:.metadata.name,TYPE:.spec.type' \
    --no-headers | awk '$3 == "LoadBalancer" {print}'
)"
if [[ -n "$load_balancers" ]]; then
  printf 'LoadBalancer Services:\n%s\n' "$load_balancers"
else
  printf 'No LoadBalancer Services found.\n'
fi

claims="$(
  kubectl get persistentvolumeclaim --all-namespaces \
    -o custom-columns='NAMESPACE:.metadata.namespace,NAME:.metadata.name,STATUS:.status.phase' \
    --no-headers
)"
if [[ -n "$claims" ]]; then
  printf 'PersistentVolumeClaims:\n%s\n' "$claims"
else
  printf 'No PersistentVolumeClaims found.\n'
fi
printf '\nRead-only audit complete. No resource was changed.\n'
