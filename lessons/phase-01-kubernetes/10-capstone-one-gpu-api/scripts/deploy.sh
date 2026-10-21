#!/usr/bin/env bash
set -euo pipefail

: "${IMAGE_REPOSITORY:?set IMAGE_REPOSITORY}"
: "${IMAGE_DIGEST:?set IMAGE_DIGEST, including sha256:}"
: "${MODEL_STORAGE_CLASS:?set MODEL_STORAGE_CLASS}"
: "${TEST_IMAGE_DIGEST:?set TEST_IMAGE_DIGEST, including sha256:}"

validate_digest() {
  local name="$1"
  local value="$2"
  local hex="${value#sha256:}"
  if [[ "$value" != sha256:* ]] ||
    [[ "${#hex}" -ne 64 ]] ||
    [[ "$hex" == *[!0-9a-f]* ]]; then
    printf '%s must be sha256:<64 lowercase hex characters>\n' "$name" >&2
    exit 1
  fi
}

validate_digest IMAGE_DIGEST "$IMAGE_DIGEST"
validate_digest TEST_IMAGE_DIGEST "$TEST_IMAGE_DIGEST"

namespace="${LAB_NAMESPACE:-one-gpu-api}"
release="${HELM_RELEASE:-one-gpu}"
args=(
  upgrade --install "$release" chart/one-gpu-api
  --namespace "$namespace"
  --create-namespace
  --set-string "image.repository=${IMAGE_REPOSITORY}"
  --set-string "image.digest=${IMAGE_DIGEST}"
  --set-string "cache.persistence.storageClassName=${MODEL_STORAGE_CLASS}"
  --set-string "test.image.digest=${TEST_IMAGE_DIGEST}"
  --wait
  --timeout 25m
)

if [[ -n "${GPU_NODE_SELECTOR_KEY:-}" ]]; then
  : "${GPU_NODE_SELECTOR_VALUE:?set GPU_NODE_SELECTOR_VALUE}"
  escaped_key="${GPU_NODE_SELECTOR_KEY//./\\.}"
  args+=(--set-string "nodeSelector.${escaped_key}=${GPU_NODE_SELECTOR_VALUE}")
fi

if [[ -n "${GPU_TAINT_KEY:-}" ]]; then
  args+=(
    --set-string "tolerations[0].key=${GPU_TAINT_KEY}"
    --set-string 'tolerations[0].operator=Exists'
    --set-string 'tolerations[0].effect=NoSchedule'
  )
fi

helm "${args[@]}"
