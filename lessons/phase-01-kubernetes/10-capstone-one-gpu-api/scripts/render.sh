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

mkdir -p artifacts
helm lint chart/one-gpu-api
helm template one-gpu chart/one-gpu-api \
  --namespace one-gpu-api \
  --set-string image.repository="$IMAGE_REPOSITORY" \
  --set-string image.digest="$IMAGE_DIGEST" \
  --set-string cache.persistence.storageClassName="$MODEL_STORAGE_CLASS" \
  --set-string test.image.digest="$TEST_IMAGE_DIGEST" \
  >artifacts/rendered.yaml

kubectl apply --dry-run=client -f artifacts/rendered.yaml >/dev/null
if grep -q 'type: LoadBalancer' artifacts/rendered.yaml; then
  printf 'refusing render containing a LoadBalancer Service\n' >&2
  exit 1
fi
printf '%s\n' \
  'rendered and client-dry-run checked artifacts/rendered.yaml'
printf '%s\n' \
  'Note: kubectl client dry-run can still use API discovery/schema data.'
