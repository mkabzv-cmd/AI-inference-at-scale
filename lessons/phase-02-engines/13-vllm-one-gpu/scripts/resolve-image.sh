#!/usr/bin/env bash
set -euo pipefail

: "${VLLM_IMAGE_TAG:=vllm/vllm-openai:v0.28.0}"
if [[ "${VLLM_IMAGE_TAG##*/}" != *:* ]]; then
  echo "VLLM_IMAGE_TAG must include an explicit tag" >&2
  exit 2
fi
repository="${VLLM_IMAGE_TAG%:*}"
mkdir -p artifacts
digest="$(
  docker buildx imagetools inspect "$VLLM_IMAGE_TAG" |
    sed -n 's/^Digest:[[:space:]]*//p' |
    head -1
)"
[[ "$digest" =~ ^sha256:[0-9a-f]{64}$ ]] || {
  echo "could not resolve image digest for $VLLM_IMAGE_TAG" >&2
  exit 1
}
printf 'VLLM_IMAGE_TAG=%q\nIMAGE_URI=%q\n' \
  "$VLLM_IMAGE_TAG" "${repository}@${digest}" \
  >artifacts/image.env
printf '%s@%s\n' "$repository" "$digest" \
  >artifacts/image-digest.txt
printf 'resolved %s\n' "$VLLM_IMAGE_TAG"
