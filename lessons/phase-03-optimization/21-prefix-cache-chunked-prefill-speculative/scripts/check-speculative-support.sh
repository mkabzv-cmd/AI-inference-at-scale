#!/usr/bin/env bash
set -euo pipefail

: "${VLLM_IMAGE:?set immutable vllm image name@sha256 digest}"
case "$VLLM_IMAGE" in *@sha256:*) ;; *) exit 2 ;; esac
mkdir -p artifacts
docker run --rm "$VLLM_IMAGE" --help |
  sed -n '/speculative/Ip' |
  tee artifacts/speculative-help.txt
echo "Read the pinned release documentation and this help before constructing"
echo "a target/draft configuration. The example JSON is deliberately invalid."
