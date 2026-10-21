#!/usr/bin/env bash
set -euo pipefail

: "${ALLOW_LESSON_38_CLEANUP:?Set ALLOW_LESSON_38_CLEANUP=yes}"
if [[ "$ALLOW_LESSON_38_CLEANUP" != "yes" ]]; then
  printf 'Refusing: ALLOW_LESSON_38_CLEANUP must equal yes\n' >&2
  exit 1
fi
kubectl delete namespace oms-l38 --ignore-not-found --wait=true
printf 'Namespace removed. Verify shared storage lifecycle and restore the GPU node group to its recorded starting capacity.\n'
