#!/usr/bin/env bash
set -euo pipefail

namespace="llm-health"
expected_part_of="open-model-systems-course"
expected_lesson="06"

context="$(kubectl config current-context 2>/dev/null || true)"
if [[ -z "$context" ]]; then
  printf 'ERROR: kubectl has no current context.\n' >&2
  exit 1
fi
printf 'current context: %s\n' "$context"

if [[ "$context" != "kind-llm-lab" &&
  "${ALLOW_NON_LAB_CONTEXT:-0}" != "1" ]]; then
  printf 'ERROR: expected context kind-llm-lab; refusing cleanup on %s.\n' \
    "$context" >&2
  printf '%s\n' \
    'For another verified disposable cluster, rerun with ALLOW_NON_LAB_CONTEXT=1.' >&2
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

if kubectl get namespace "$namespace" >/dev/null 2>&1; then
  printf 'ERROR: namespace %s still exists.\n' "$namespace" >&2
  exit 1
fi

printf 'cleanup verified: namespace %s does not exist\n' "$namespace"
