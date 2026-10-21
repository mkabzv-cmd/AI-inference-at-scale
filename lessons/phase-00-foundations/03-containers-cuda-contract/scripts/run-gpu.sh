#!/usr/bin/env bash
set -euo pipefail

image_name="${IMAGE_NAME:-open-models/cuda-contract:lesson03}"
mkdir -p results
docker run --rm \
  --gpus all \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp \
  --volume "$(pwd)/results:/results" \
  "$image_name" \
  --require-gpu \
  --output /results/gpu.json
