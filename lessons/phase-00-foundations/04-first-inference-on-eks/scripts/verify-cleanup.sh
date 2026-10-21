#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION}"
: "${EKS_CLUSTER_NAME:?Set EKS_CLUSTER_NAME}"
: "${GPU_NODEGROUP_NAME:?Set GPU_NODEGROUP_NAME}"
: "${LAB_NAMESPACE:?Set LAB_NAMESPACE}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
lesson_dir="$(cd "$script_dir/.." && pwd)"
source "$script_dir/assert-target.sh"
assert_safe_namespace_name
assert_kube_context_matches_cluster

failures=0
namespace="$(
  kubectl get namespace "$LAB_NAMESPACE" \
    --ignore-not-found \
    -o name
)"
if [[ -n "$namespace" ]]; then
  printf '[fail] namespace still exists: %s\n' "$LAB_NAMESPACE"
  failures=$((failures + 1))
else
  printf '[ok] namespace absent: %s\n' "$LAB_NAMESPACE"
fi

baseline_file="$lesson_dir/.lab/nodegroup-before.json"
if [[ ! -f "$baseline_file" ]]; then
  printf '[fail] missing saved node-group baseline: %s\n' "$baseline_file"
  exit 1
fi

read -r saved_account saved_region saved_cluster saved_nodegroup \
  saved_desired saved_minimum saved_maximum < <(
  python3 -c '
import json
import sys

record = json.load(open(sys.argv[1], encoding="utf-8"))
scaling = record["scaling"]
print(
    record["account_id"],
    record["region"],
    record["cluster"],
    record["nodegroup"],
    scaling["desired"],
    scaling["minimum"],
    scaling["maximum"],
)
' "$baseline_file"
)
account_id="$(aws sts get-caller-identity --query Account --output text)"
if [[ "$saved_account" != "$account_id" ||
  "$saved_region" != "$AWS_REGION" ||
  "$saved_cluster" != "$EKS_CLUSTER_NAME" ||
  "$saved_nodegroup" != "$GPU_NODEGROUP_NAME" ]]; then
  printf '[fail] saved baseline belongs to a different AWS target\n'
  exit 1
fi

read -r desired minimum maximum < <(
  aws eks describe-nodegroup \
    --region "$AWS_REGION" \
    --cluster-name "$EKS_CLUSTER_NAME" \
    --nodegroup-name "$GPU_NODEGROUP_NAME" \
    --query 'nodegroup.[scalingConfig.desiredSize,scalingConfig.minSize,scalingConfig.maxSize]' \
    --output text
)
if [[ "$desired" == "$saved_desired" &&
  "$minimum" == "$saved_minimum" &&
  "$maximum" == "$saved_maximum" ]]; then
  printf '[ok] node-group scaling restored: desired=%s min=%s max=%s\n' \
    "$desired" "$minimum" "$maximum"
else
  printf '[fail] node-group scaling was not restored\n'
  printf '  actual:   desired=%s min=%s max=%s\n' \
    "$desired" "$minimum" "$maximum"
  printf '  expected: desired=%s min=%s max=%s\n' \
    "$saved_desired" "$saved_minimum" "$saved_maximum"
  failures=$((failures + 1))
fi

if [[ "$saved_desired" != "0" || "$saved_minimum" != "0" ]]; then
  printf '[fail] saved baseline was not an idle min=0 desired=0 lab group\n'
  failures=$((failures + 1))
fi

nodes="$(
  kubectl get nodes \
    -l "eks.amazonaws.com/nodegroup=$GPU_NODEGROUP_NAME" \
    -o name
)"
if [[ -n "$nodes" ]]; then
  printf '[fail] GPU node objects still remain:\n%s\n' "$nodes"
  failures=$((failures + 1))
else
  printf '[ok] no Kubernetes node object remains for the GPU node group\n'
fi

leftovers="$(
  kubectl get all --all-namespaces \
    -l app.kubernetes.io/part-of=open-model-systems-learning,course.lesson=04 \
    --no-headers
)"
if [[ -n "$leftovers" ]]; then
  printf '[fail] labeled lesson resources remain:\n%s\n' "$leftovers"
  failures=$((failures + 1))
else
  printf '[ok] no labeled lesson workloads remain\n'
fi

if (( failures > 0 )); then
  printf 'Cleanup verification failed with %d problem(s).\n' "$failures"
  exit 1
fi
printf 'Cleanup verification passed.\n'
