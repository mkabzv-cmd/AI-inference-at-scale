#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION}"
: "${ECR_REPOSITORY:?Set ECR_REPOSITORY}"
: "${IMAGE_TAG:?Set IMAGE_TAG}"

mkdir -p .lab
account_id="$(aws sts get-caller-identity --query Account --output text)"
registry="${account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com"
image_with_tag="${registry}/${ECR_REPOSITORY}:${IMAGE_TAG}"

read -r tag_mutability scan_on_push < <(
  aws ecr describe-repositories \
    --region "$AWS_REGION" \
    --repository-names "$ECR_REPOSITORY" \
    --query 'repositories[0].[imageTagMutability,imageScanningConfiguration.scanOnPush]' \
    --output text
)
if [[ "$tag_mutability" != "IMMUTABLE" || "$scan_on_push" != "True" ]]; then
  printf '%s\n' \
    'ECR repository must use IMMUTABLE tags and scan-on-push before this build.' >&2
  exit 1
fi

temporary_docker_config="$(mktemp -d)"
cleanup_docker_config() {
  rm -r -- "$temporary_docker_config"
}
trap cleanup_docker_config EXIT

current_docker_context="$(docker context show)"
source_docker_config="${DOCKER_CONFIG:-${HOME:?HOME is required}/.docker}"
if [[ -d "$source_docker_config/contexts" ]]; then
  cp -R "$source_docker_config/contexts" "$temporary_docker_config/contexts"
fi
python3 - "$temporary_docker_config/config.json" "$current_docker_context" <<'PY'
import json
import sys
from pathlib import Path

path, current_context = sys.argv[1:]
Path(path).write_text(
    json.dumps({"currentContext": current_context}) + "\n",
    encoding="utf-8",
)
PY
DOCKER_CONFIG="$temporary_docker_config" docker info >/dev/null

aws ecr get-login-password --region "$AWS_REGION" \
  | DOCKER_CONFIG="$temporary_docker_config" \
    docker login --username AWS --password-stdin "$registry"

docker build \
  --platform linux/amd64 \
  --tag "$image_with_tag" \
  .
DOCKER_CONFIG="$temporary_docker_config" docker push "$image_with_tag"

digest="$(
  aws ecr describe-images \
    --region "$AWS_REGION" \
    --repository-name "$ECR_REPOSITORY" \
    --image-ids "imageTag=$IMAGE_TAG" \
    --query 'imageDetails[0].imageDigest' \
    --output text
)"
if [[ ! "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  printf 'Could not resolve a valid ECR digest; received: %s\n' "$digest" >&2
  exit 1
fi

printf 'IMAGE_URI_WITH_DIGEST=%s/%s@%s\n' \
  "$registry" "$ECR_REPOSITORY" "$digest" > .lab/image.env
printf 'IMAGE_URI_WITH_TAG=%s\n' "$image_with_tag" >> .lab/image.env
printf 'IMAGE_DIGEST=%s\n' "$digest" >> .lab/image.env

printf 'Pushed: %s\n' "$image_with_tag"
printf 'Resolved immutable digest: %s\n' "$digest"
printf 'Private deployment values written to .lab/image.env\n'
