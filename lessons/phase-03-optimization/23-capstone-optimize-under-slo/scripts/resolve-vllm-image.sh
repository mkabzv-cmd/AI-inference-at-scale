#!/usr/bin/env bash
set -euo pipefail

command -v docker >/dev/null
tag="${VLLM_IMAGE_TAG:-vllm/vllm-openai:v0.28.0}"
if [[ "${tag##*/}" != *:* ]]; then
  echo "VLLM_IMAGE_TAG must include an explicit tag" >&2
  exit 2
fi
repository="${tag%:*}"
digest="$(
  docker buildx imagetools inspect "$tag" |
    sed -n 's/^Digest:[[:space:]]*//p' |
    head -1
)"
[[ "$digest" =~ ^sha256:[0-9a-f]{64}$ ]] || {
  echo "failed to resolve $tag" >&2
  exit 1
}
printf '%s@%s\n' "$repository" "$digest"
