#!/usr/bin/env bash
set -euo pipefail

lesson_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
repo_root="$(cd "$lesson_dir/../../.." && pwd)"
: "${BASE_IMAGE_REF:?Set BASE_IMAGE_REF to name@sha256:<64 lowercase hex>}"
: "${IMAGE_TAG:?Set IMAGE_TAG to the registry tag you will build and push}"

if [[ ! "$BASE_IMAGE_REF" =~ ^[A-Za-z0-9._:/-]+@sha256:[a-f0-9]{64}$ ]]; then
  echo "BASE_IMAGE_REF must be digest pinned" >&2
  exit 1
fi

docker build \
  --build-arg "BASE_IMAGE=$BASE_IMAGE_REF" \
  --file "$lesson_dir/container/Dockerfile" \
  --tag "$IMAGE_TAG" \
  "$repo_root"
echo "built $IMAGE_TAG from digest-pinned base; push and deploy by registry digest"
