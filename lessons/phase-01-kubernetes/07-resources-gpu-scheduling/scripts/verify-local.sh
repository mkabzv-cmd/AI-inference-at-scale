#!/usr/bin/env bash
set -euo pipefail

expected_node="${1:-}"
if [[ -z "$expected_node" ]]; then
  printf 'Usage: %s SIMULATED_GPU_NODE_NAME\n' "$0" >&2
  exit 2
fi

namespace="gpu-scheduling"
kubectl get namespace "$namespace" >/dev/null
kubectl get node "$expected_node" >/dev/null

label="$(kubectl get node "$expected_node" \
  -o jsonpath='{.metadata.labels.lesson\.open-model-systems/accelerator}')"
taint="$(kubectl get node "$expected_node" \
  -o jsonpath='{range .spec.taints[?(@.key=="nvidia.com/gpu")]}{.value}{":"}{.effect}{"\n"}{end}')"

if [[ "$label" != "simulated-gpu" ]]; then
  printf 'ERROR: expected simulated-gpu label on %s.\n' "$expected_node" >&2
  exit 1
fi
if [[ "$taint" != "true:NoSchedule" ]]; then
  printf 'ERROR: expected nvidia.com/gpu=true:NoSchedule on %s; got %s.\n' \
    "$expected_node" "${taint:-<none>}" >&2
  exit 1
fi

kubectl wait --for=condition=Ready pod/simulated-gpu-workload \
  -n "$namespace" --timeout=60s
kubectl wait --for=condition=Ready pod/ordinary-workload \
  -n "$namespace" --timeout=60s
actual_node="$(kubectl get pod simulated-gpu-workload -n "$namespace" \
  -o jsonpath='{.spec.nodeName}')"

if [[ "$actual_node" != "$expected_node" ]]; then
  printf 'ERROR: simulated workload scheduled on %s, expected %s.\n' \
    "$actual_node" "$expected_node" >&2
  exit 1
fi

ordinary_node="$(kubectl get pod ordinary-workload -n "$namespace" \
  -o jsonpath='{.spec.nodeName}')"
if [[ -z "$ordinary_node" ]]; then
  printf 'ERROR: ordinary workload is not bound to a node.\n' >&2
  exit 1
fi
if [[ "$ordinary_node" == "$expected_node" ]]; then
  printf 'ERROR: ordinary workload landed on tainted node %s.\n' \
    "$expected_node" >&2
  exit 1
fi

printf 'simulated accelerator workload node: %s\n' "$actual_node"
printf 'ordinary workload node: %s\n' "$ordinary_node"
printf 'lesson 07 local verification passed\n'
