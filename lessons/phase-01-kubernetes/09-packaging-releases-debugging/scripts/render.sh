#!/usr/bin/env bash
set -euo pipefail

: "${IMAGE_REPOSITORY:?set IMAGE_REPOSITORY}"
: "${IMAGE_DIGEST:?set IMAGE_DIGEST, including sha256:}"

mkdir -p artifacts
helm lint chart/lesson-service
helm template course chart/lesson-service \
  --namespace packaging-lab \
  --set-string image.repository="$IMAGE_REPOSITORY" \
  --set-string image.digest="$IMAGE_DIGEST" \
  >artifacts/rendered.yaml

kubectl apply --dry-run=client -f artifacts/rendered.yaml >/dev/null
printf 'rendered and client-validated artifacts/rendered.yaml\n'
