#!/usr/bin/env bash
set -euo pipefail

: "${CONFIRM_LAB_CONTEXT:?set to the exact intended kubectl context}"
context="$(kubectl config current-context)"
[[ "$context" == "$CONFIRM_LAB_CONTEXT" ]] || {
  echo "refusing context $context" >&2
  exit 2
}
kubectl delete namespace oms-lesson-23 --ignore-not-found --wait=true
if kubectl get namespace oms-lesson-23 >/dev/null 2>&1; then
  echo "namespace still exists" >&2
  exit 1
fi
echo "namespace removal verified; restore GPU node-group size separately"
