#!/usr/bin/env bash
set -euo pipefail

: "${ALLOW_LESSON_39_CLEANUP:?Set ALLOW_LESSON_39_CLEANUP=yes}"
if [[ "$ALLOW_LESSON_39_CLEANUP" != "yes" ]]; then
  printf 'Refusing: ALLOW_LESSON_39_CLEANUP must equal yes\n' >&2
  exit 1
fi
kubectl delete namespace oms-l39 --ignore-not-found --wait=true
printf 'Namespace removed. Verify PVC policy separately and restore GPU node capacity.\n'
