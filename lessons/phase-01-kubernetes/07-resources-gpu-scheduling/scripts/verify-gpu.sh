#!/usr/bin/env bash
set -euo pipefail

namespace="gpu-scheduling"
pod="nvidia-smi"
expected_node="${1:-}"

if [[ -z "$expected_node" ]]; then
  printf 'Usage: %s EXPECTED_GPU_NODE_NAME\n' "$0" >&2
  exit 2
fi

phase="$(kubectl get pod "$pod" -n "$namespace" -o jsonpath='{.status.phase}')"
if [[ "$phase" != "Succeeded" ]]; then
  printf 'ERROR: expected %s/%s to be Succeeded; got %s.\n' \
    "$namespace" "$pod" "$phase" >&2
  kubectl describe pod "$pod" -n "$namespace" >&2
  exit 1
fi

requested="$(kubectl get pod "$pod" -n "$namespace" \
  -o jsonpath='{.spec.containers[0].resources.requests.nvidia\.com/gpu}')"
limited="$(kubectl get pod "$pod" -n "$namespace" \
  -o jsonpath='{.spec.containers[0].resources.limits.nvidia\.com/gpu}')"
node="$(kubectl get pod "$pod" -n "$namespace" -o jsonpath='{.spec.nodeName}')"
allocatable="$(kubectl get node "$node" \
  -o jsonpath='{.status.allocatable.nvidia\.com/gpu}')"
logs="$(kubectl logs "$pod" -n "$namespace")"

if [[ "$node" != "$expected_node" ]]; then
  printf 'ERROR: GPU Pod ran on %s, expected the reviewed Node %s.\n' \
    "$node" "$expected_node" >&2
  exit 1
fi
if [[ "$requested" != "1" || "$limited" != "1" ]]; then
  printf 'ERROR: GPU request/limit must both equal 1.\n' >&2
  exit 1
fi
if [[ -z "$allocatable" || "$allocatable" == "0" ]]; then
  printf 'ERROR: node %s does not advertise allocatable nvidia.com/gpu.\n' \
    "$node" >&2
  exit 1
fi
if [[ -z "$logs" ]]; then
  printf 'ERROR: nvidia-smi returned no output.\n' >&2
  exit 1
fi

printf 'scheduled node: %s\n' "$node"
printf 'node allocatable nvidia.com/gpu: %s\n' "$allocatable"
printf 'nvidia-smi output:\n%s\n' "$logs"
printf 'lesson 07 GPU verification passed\n'
