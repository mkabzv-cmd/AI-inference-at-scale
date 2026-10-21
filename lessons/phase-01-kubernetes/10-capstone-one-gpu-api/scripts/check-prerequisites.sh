#!/usr/bin/env bash
set -euo pipefail

required=(aws kubectl helm docker curl python3)
missing=0
for command_name in "${required[@]}"; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf 'missing required command: %s\n' "$command_name" >&2
    missing=1
  fi
done
[[ "$missing" -eq 0 ]] || exit 1
docker buildx version >/dev/null

: "${AWS_REGION:?set AWS_REGION}"
: "${EKS_CLUSTER:?set EKS_CLUSTER}"
: "${GPU_NODEGROUP:?set GPU_NODEGROUP}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/assert-target.sh"
assert_eks_target
assert_namespace_owned_or_absent
namespace="$(lesson_namespace)"

require_kube_permission() {
  if ! kubectl auth can-i "$@" --quiet; then
    printf 'Kubernetes authorization denied: kubectl auth can-i %s\n' \
      "$*" >&2
    return 1
  fi
  printf 'Kubernetes authorization allows: %s\n' "$*"
}

printf 'AWS identity:\n'
aws sts get-caller-identity
printf 'cluster=%s region=%s nodegroup=%s\n' \
  "$EKS_CLUSTER" "$AWS_REGION" "$GPU_NODEGROUP"
expected_server="$(
  aws eks describe-cluster \
    --region "$AWS_REGION" \
    --name "$EKS_CLUSTER" \
    --query 'cluster.endpoint' \
    --output text
)"
active_server="$(
  kubectl config view --minify \
    -o jsonpath='{.clusters[0].cluster.server}'
)"
if [[ "$active_server" != "$expected_server" ]]; then
  printf 'refusing to continue: kubectl points at %s\n' "$active_server" >&2
  printf 'but EKS_CLUSTER=%s points at %s\n' \
    "$EKS_CLUSTER" "$expected_server" >&2
  exit 1
fi

aws eks describe-cluster \
  --region "$AWS_REGION" \
  --name "$EKS_CLUSTER" \
  --query 'cluster.{name:name,status:status,version:version}' \
  --output table
aws eks describe-nodegroup \
  --region "$AWS_REGION" \
  --cluster-name "$EKS_CLUSTER" \
  --nodegroup-name "$GPU_NODEGROUP" \
  --query 'nodegroup.{status:status,instanceTypes:instanceTypes,scaling:scalingConfig}' \
  --output table

printf 'kubectl context: %s\n' "$(kubectl config current-context)"
kubectl cluster-info
require_kube_permission create namespaces
require_kube_permission delete namespaces
require_kube_permission create secrets --namespace "$namespace"
require_kube_permission create serviceaccounts --namespace "$namespace"
require_kube_permission create deployments.apps --namespace "$namespace"
require_kube_permission create services --namespace "$namespace"
require_kube_permission create persistentvolumeclaims --namespace "$namespace"
require_kube_permission delete persistentvolumeclaims --namespace "$namespace"

helm lint chart/one-gpu-api
helm template one-gpu chart/one-gpu-api \
  --namespace "$namespace" >/dev/null

printf 'GPU capacity currently advertised:\n'
kubectl get nodes \
  -o custom-columns=NAME:.metadata.name,INSTANCE:.metadata.labels.node\\.kubernetes\\.io/instance-type,GPU:.status.allocatable.nvidia\\.com/gpu

if [[ "${REQUIRE_GPU_READY:-0}" == "1" ]] &&
  ! kubectl get nodes -o json |
    python3 -c '
import json
import sys

nodes = json.load(sys.stdin)["items"]
for node in nodes:
    ready = any(
        condition["type"] == "Ready" and condition["status"] == "True"
        for condition in node["status"].get("conditions", [])
    )
    gpu = int(node["status"].get("allocatable", {}).get("nvidia.com/gpu", 0))
    if ready and gpu > 0:
        raise SystemExit(0)
raise SystemExit(1)
'; then
  printf 'no Ready node advertises allocatable nvidia.com/gpu\n' >&2
  exit 1
fi

printf 'preflight checks complete\n'
