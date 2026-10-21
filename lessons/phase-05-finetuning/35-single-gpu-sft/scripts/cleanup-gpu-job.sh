#!/usr/bin/env bash
set -euo pipefail

: "${ALLOW_LESSON_35_CLEANUP:?Set ALLOW_LESSON_35_CLEANUP=yes}"
if [[ "$ALLOW_LESSON_35_CLEANUP" != "yes" ]]; then
  printf 'Refusing: ALLOW_LESSON_35_CLEANUP must equal yes\n' >&2
  exit 1
fi

kubectl delete namespace oms-l35 --ignore-not-found --wait=true
if kubectl get namespace oms-l35 >/dev/null 2>&1; then
  printf 'Namespace still exists\n' >&2
  exit 1
fi
printf 'Kubernetes lesson namespace is absent; separately restore and verify node-group capacity\n'
