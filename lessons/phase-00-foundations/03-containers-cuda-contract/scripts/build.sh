#!/usr/bin/env bash
set -euo pipefail

image_name="${IMAGE_NAME:-open-models/cuda-contract:lesson03}"
base_image="${BASE_IMAGE:-pytorch/pytorch@sha256:c8268a92a69bd500f8be0e665b2630ee006dadaf7bfbc24249141b15ff622755}"
if [[ ! "$base_image" =~ @sha256:[0-9a-f]{64}$ ]]; then
  printf '%s\n' \
    'BASE_IMAGE must be an immutable image reference ending in @sha256:<64 lowercase hex>.' >&2
  exit 2
fi
mkdir -p results

docker build \
  --platform linux/amd64 \
  --build-arg "BASE_IMAGE=$base_image" \
  --label "course.lesson=03" \
  --tag "$image_name" \
  .

image_id="$(docker image inspect "$image_name" --format '{{.Id}}')"
repo_digests="$(docker image inspect "$image_name" --format '{{json .RepoDigests}}')"

python3 - "$image_name" "$base_image" "$image_id" "$repo_digests" <<'PY'
import json
import sys
from pathlib import Path

image, base, image_id, repo_digests = sys.argv[1:]
Path("results/image.json").write_text(
    json.dumps(
        {
            "image": image,
            "base_image": base,
            "image_id": image_id,
            "repo_digests": json.loads(repo_digests),
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
PY

printf 'image ID: %s\n' "$image_id"
if [[ "$repo_digests" == "[]" ]]; then
  printf 'repo digest: unavailable until the image is pushed/pulled by digest\n'
else
  printf 'repo digests: %s\n' "$repo_digests"
fi
printf 'metadata written to results/image.json\n'
