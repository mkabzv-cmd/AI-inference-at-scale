#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:?Set LAB_NAMESPACE}"
: "${CONFIRM_NAMESPACE:?Set CONFIRM_NAMESPACE to the exact same namespace}"

if [[ ! "$LAB_NAMESPACE" =~ ^oms-lesson-46-[a-z0-9-]+$ ]]; then
  printf 'Refusing namespace outside oms-lesson-46-* scope\n' >&2
  exit 1
fi
if [[ "$CONFIRM_NAMESPACE" != "$LAB_NAMESPACE" ]]; then
  printf 'Namespace confirmation does not match\n' >&2
  exit 1
fi

pod="$(
  kubectl get pod \
    -n "$LAB_NAMESPACE" \
    -l app.kubernetes.io/name=oms-model \
    -o jsonpath='{.items[0].metadata.name}'
)"
if [[ -z "$pod" ]]; then
  printf 'No target Pod found\n' >&2
  exit 1
fi

kubectl delete pod "$pod" -n "$LAB_NAMESPACE" --wait=false
printf 'Deleted %s; observe queue, readiness, replacement, and request results\n' \
  "$pod"
