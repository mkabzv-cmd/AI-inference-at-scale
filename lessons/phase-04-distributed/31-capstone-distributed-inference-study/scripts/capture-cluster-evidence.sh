#!/usr/bin/env bash
set -euo pipefail

label="${1:-snapshot}"
: "${AWS_REGION:?set AWS_REGION}"
: "${EKS_CLUSTER:?set EKS_CLUSTER}"
: "${GPU_NODEGROUP:?set GPU_NODEGROUP}"
: "${LAB_NAMESPACE:?set LAB_NAMESPACE}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/../../common/scripts/assert-eks-target.sh"
if [[ ! "$label" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
  printf 'snapshot label must be lowercase letters, digits, and hyphens\n' >&2
  exit 2
fi
directory="artifacts/cluster-${label}"
mkdir -p "$directory"
kubectl get nodes \
  -l "eks.amazonaws.com/nodegroup=${GPU_NODEGROUP}" \
  -o yaml >"$directory/nodes.yaml"
kubectl get pods --all-namespaces -o wide >"$directory/pods.txt"
kubectl version -o json >"$directory/kubernetes-version.json"
aws eks describe-nodegroup \
  --region "$AWS_REGION" \
  --cluster-name "$EKS_CLUSTER" \
  --nodegroup-name "$GPU_NODEGROUP" \
  --query \
  'nodegroup.{name:nodegroupName,status:status,instances:instanceTypes,scaling:scalingConfig,amiType:amiType,releaseVersion:releaseVersion}' \
  --output json >"$directory/nodegroup.json"
printf 'cluster evidence saved under %s; sanitize before publishing\n' "$directory"
