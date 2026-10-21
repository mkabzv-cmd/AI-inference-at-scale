#!/usr/bin/env bash
set -euo pipefail

docker rm --force open-models-l15 >/dev/null 2>&1 || true
if docker ps --format '{{.Names}}' | grep -qx open-models-l15; then
  echo "server container remains" >&2
  exit 1
fi
if [[ -n "${LAB_NAMESPACE:-}" ]]; then
  if [[ ! "$LAB_NAMESPACE" =~ ^open-models-[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] ||
    (( ${#LAB_NAMESPACE} > 63 )); then
    echo "refusing unexpected namespace" >&2
    exit 1
  fi
  if kubectl get namespace "$LAB_NAMESPACE" >/dev/null 2>&1; then
    owner="$(
      kubectl get namespace "$LAB_NAMESPACE" \
        -o jsonpath='{.metadata.labels.app\.kubernetes\.io/part-of}'
    )"
    lesson="$(
      kubectl get namespace "$LAB_NAMESPACE" \
        -o jsonpath='{.metadata.labels.open-model-systems\.io/lesson}'
    )"
    [[ "$owner" == "open-model-systems-course" && "$lesson" == "15" ]] || {
      echo "refusing to delete a namespace without lesson-15 ownership labels" >&2
      exit 1
    }
  fi
  kubectl delete namespace "$LAB_NAMESPACE" --ignore-not-found --wait=true
  ! kubectl get namespace "$LAB_NAMESPACE" >/dev/null 2>&1
fi
printf 'server stopped. GGUF files and built images were retained intentionally.\n'
printf 'Remove them only after checking paths: artifacts/models and your open-models image tags.\n'
