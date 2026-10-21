#!/usr/bin/env bash
set -euo pipefail

node="${1:-}"
namespace="gpu-scheduling"
expected_part_of="open-model-systems-course"
expected_lesson="07"

if [[ -z "$node" ]]; then
  printf 'Usage: %s SIMULATED_GPU_NODE_NAME\n' "$0" >&2
  exit 2
fi

context="$(kubectl config current-context 2>/dev/null || true)"
if [[ -z "$context" ]]; then
  printf 'ERROR: kubectl has no current context.\n' >&2
  exit 1
fi
printf 'current context: %s\n' "$context"

if [[ "$context" != "kind-llm-scheduler-lab" &&
  "${ALLOW_NON_LAB_CONTEXT:-0}" != "1" ]]; then
  printf 'ERROR: expected context kind-llm-scheduler-lab; refusing cleanup on %s.\n' \
    "$context" >&2
  printf '%s\n' \
    'For another verified disposable cluster, set ALLOW_NON_LAB_CONTEXT=1.' >&2
  exit 1
fi

kubectl get node "$node" >/dev/null

marker="$(kubectl get node "$node" \
  -o jsonpath='{.metadata.labels.lesson\.open-model-systems/accelerator}')"
taint="$(kubectl get node "$node" \
  -o jsonpath='{range .spec.taints[?(@.key=="nvidia.com/gpu")]}{.value}{":"}{.effect}{"\n"}{end}')"

if [[ -n "$marker" && "$marker" != "simulated-gpu" ]]; then
  printf 'ERROR: refusing cleanup: node %s has unexpected marker %s.\n' \
    "$node" "$marker" >&2
  exit 1
fi
if [[ -n "$taint" && "$taint" != "true:NoSchedule" ]]; then
  printf 'ERROR: refusing cleanup: node %s has unexpected GPU taint %s.\n' \
    "$node" "$taint" >&2
  exit 1
fi
if [[ -n "$taint" && "$marker" != "simulated-gpu" ]]; then
  printf 'ERROR: refusing to remove GPU taint without the course marker on %s.\n' \
    "$node" >&2
  exit 1
fi

if kubectl get namespace "$namespace" >/dev/null 2>&1; then
  part_of="$(kubectl get namespace "$namespace" \
    -o jsonpath='{.metadata.labels.app\.kubernetes\.io/part-of}')"
  lesson="$(kubectl get namespace "$namespace" \
    -o jsonpath='{.metadata.labels.lesson\.open-model-systems/id}')"
  if [[ "$part_of" != "$expected_part_of" ||
    "$lesson" != "$expected_lesson" ]]; then
    printf 'ERROR: refusing to delete namespace %s: unexpected labels '\
'part-of=%s lesson=%s.\n' \
      "$namespace" "${part_of:-<missing>}" "${lesson:-<missing>}" >&2
    exit 1
  fi
  kubectl delete namespace "$namespace" --wait=true --timeout=120s
fi

if [[ "$taint" == "true:NoSchedule" ]]; then
  kubectl taint node "$node" nvidia.com/gpu:NoSchedule-
fi
if [[ "$marker" == "simulated-gpu" ]]; then
  kubectl label node "$node" lesson.open-model-systems/accelerator-
fi

remaining_marker="$(kubectl get node "$node" \
  -o jsonpath='{.metadata.labels.lesson\.open-model-systems/accelerator}')"
remaining_taint="$(kubectl get node "$node" \
  -o jsonpath='{range .spec.taints[?(@.key=="nvidia.com/gpu")]}{.value}{":"}{.effect}{"\n"}{end}')"
if [[ -n "$remaining_marker" || -n "$remaining_taint" ]]; then
  printf 'ERROR: lesson marker or GPU taint remains on %s.\n' "$node" >&2
  exit 1
fi
if kubectl get namespace "$namespace" >/dev/null 2>&1; then
  printf 'ERROR: namespace %s still exists.\n' "$namespace" >&2
  exit 1
fi

printf 'verified lesson label and taint are absent from %s\n' "$node"
printf 'local lesson objects cleaned up\n'
