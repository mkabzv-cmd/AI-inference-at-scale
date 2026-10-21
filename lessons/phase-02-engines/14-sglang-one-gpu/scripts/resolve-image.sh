#!/usr/bin/env bash
set -euo pipefail

: "${SGLANG_IMAGE_TAG:=lmsysorg/sglang:v0.5.21-cu130}"
if [[ "${SGLANG_IMAGE_TAG##*/}" != *:* ]]; then
  echo "SGLANG_IMAGE_TAG must include an explicit tag" >&2
  exit 2
fi
repository="${SGLANG_IMAGE_TAG%:*}"
mkdir -p artifacts
digest="$(
  docker buildx imagetools inspect "$SGLANG_IMAGE_TAG" |
    sed -n 's/^Digest:[[:space:]]*//p' |
    head -1
)"
[[ "$digest" =~ ^sha256:[0-9a-f]{64}$ ]] || {
  echo "digest resolution failed" >&2
  exit 1
}
printf 'SGLANG_IMAGE_TAG=%q\nIMAGE_URI=%q\n' \
  "$SGLANG_IMAGE_TAG" "${repository}@${digest}" \
  >artifacts/image.env
printf '%s@%s\n' "$repository" "$digest" \
  >artifacts/image-digest.txt
printf 'resolved %s\n' "$SGLANG_IMAGE_TAG"
