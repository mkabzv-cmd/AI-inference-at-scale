#!/usr/bin/env bash
set -euo pipefail

: "${CPU_IMAGE_TAG:=open-models/llama-cpp:v0.5.0-cpu}"
: "${UBUNTU_TAG:=ubuntu:24.04}"
if [[ "${UBUNTU_TAG##*/}" != *:* ]]; then
  echo "UBUNTU_TAG must include an explicit tag" >&2
  exit 2
fi
mkdir -p artifacts
digest="$(
  docker buildx imagetools inspect "$UBUNTU_TAG" |
    sed -n 's/^Digest:[[:space:]]*//p' | head -1
)"
[[ "$digest" =~ ^sha256:[0-9a-f]{64}$ ]] || {
  echo "base digest resolution failed" >&2
  exit 1
}
base="${UBUNTU_TAG%:*}@${digest}"
docker build \
  --file docker/Dockerfile.cpu \
  --build-arg "BUILD_IMAGE=$base" \
  --build-arg "RUNTIME_IMAGE=$base" \
  --tag "$CPU_IMAGE_TAG" .
docker image inspect "$CPU_IMAGE_TAG" \
  --format '{{json .RepoDigests}}' >artifacts/cpu-image-repodigests.json
printf 'CPU_IMAGE_TAG=%q\n' "$CPU_IMAGE_TAG" >artifacts/cpu-image.env
printf 'built %s from %s\n' "$CPU_IMAGE_TAG" "$base"
