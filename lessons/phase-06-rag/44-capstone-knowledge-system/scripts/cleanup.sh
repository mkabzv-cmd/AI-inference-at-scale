#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${COURSE_NAMESPACE:?Set COURSE_NAMESPACE}"
manifest="$lesson_dir/artifacts/rendered-knowledge-service.yaml"
if [[ ! -f "$manifest" ]]; then
  echo "rendered manifest is absent; nothing will be deleted" >&2
  exit 1
fi
manifest_namespaces="$(
  sed -n 's/^  namespace: //p' "$manifest" | LC_ALL=C sort -u
)"
if [[ "$manifest_namespaces" != "$COURSE_NAMESPACE" ]]; then
  echo "rendered manifest namespace does not match COURSE_NAMESPACE" >&2
  exit 1
fi
kubectl config current-context
kubectl delete -f "$manifest" --ignore-not-found
echo "deleted lesson resources from $COURSE_NAMESPACE; namespace was retained"
