#!/usr/bin/env bash
set -euo pipefail

: "${CUDA_IMAGE_TAG:=open-models/llama-cpp:v0.5.0-cuda12.4}"
: "${CUDA_BUILD_TAG:=nvidia/cuda:12.4.1-devel-ubuntu22.04}"
: "${CUDA_RUNTIME_TAG:=nvidia/cuda:12.4.1-runtime-ubuntu22.04}"
for tagged_image in "$CUDA_BUILD_TAG" "$CUDA_RUNTIME_TAG"; do
  if [[ "${tagged_image##*/}" != *:* ]]; then
    echo "CUDA base images must include explicit tags" >&2
    exit 2
  fi
done
mkdir -p artifacts

resolve() {
  docker buildx imagetools inspect "$1" |
    sed -n 's/^Digest:[[:space:]]*//p' |
    head -1
}
build_digest="$(resolve "$CUDA_BUILD_TAG")"
runtime_digest="$(resolve "$CUDA_RUNTIME_TAG")"
[[ "$build_digest" =~ ^sha256:[0-9a-f]{64}$ ]] &&
  [[ "$runtime_digest" =~ ^sha256:[0-9a-f]{64}$ ]] || {
    echo "CUDA base digest resolution failed" >&2
    exit 1
  }
build_image="${CUDA_BUILD_TAG%:*}@${build_digest}"
runtime_image="${CUDA_RUNTIME_TAG%:*}@${runtime_digest}"
docker build \
  --file docker/Dockerfile.cuda \
  --build-arg "BUILD_IMAGE=$build_image" \
  --build-arg "RUNTIME_IMAGE=$runtime_image" \
  --tag "$CUDA_IMAGE_TAG" .
printf '%s\n%s\n' "$build_image" "$runtime_image" >artifacts/cuda-base-digests.txt
printf 'CUDA_IMAGE_TAG=%q\n' "$CUDA_IMAGE_TAG" >artifacts/cuda-image.env
printf 'built %s; push it and deploy its registry digest, never this local tag\n' \
  "$CUDA_IMAGE_TAG"
