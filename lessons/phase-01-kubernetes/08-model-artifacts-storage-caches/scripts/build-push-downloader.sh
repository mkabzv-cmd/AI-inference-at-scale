#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:?set AWS_REGION, for example us-east-1}"
: "${AWS_ACCOUNT_ID:?set AWS_ACCOUNT_ID from aws sts get-caller-identity}"

actual_account_id="$(
  aws sts get-caller-identity --query Account --output text
)"
if [[ "$actual_account_id" != "$AWS_ACCOUNT_ID" ]]; then
  printf 'AWS_ACCOUNT_ID=%s but active credentials use %s\n' \
    "$AWS_ACCOUNT_ID" "$actual_account_id" >&2
  exit 1
fi

repository="${ECR_REPOSITORY:-open-model-course/model-downloader}"
tag="${IMAGE_TAG:-lesson-08-v1}"
registry="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
image="${registry}/${repository}:${tag}"

aws ecr describe-repositories \
  --region "$AWS_REGION" \
  --repository-names "$repository" >/dev/null 2>&1 ||
  aws ecr create-repository \
    --region "$AWS_REGION" \
    --repository-name "$repository" \
    --image-scanning-configuration scanOnPush=true >/dev/null

aws ecr get-login-password --region "$AWS_REGION" |
  docker login --username AWS --password-stdin "$registry"

docker build --platform linux/amd64 --tag "$image" downloader
docker push "$image"

digest="$(
  aws ecr describe-images \
    --region "$AWS_REGION" \
    --repository-name "$repository" \
    --image-ids imageTag="$tag" \
    --query 'imageDetails[0].imageDigest' \
    --output text
)"
digest_hex="${digest#sha256:}"
if [[ "$digest" != sha256:* ]] ||
  [[ "${#digest_hex}" -ne 64 ]] ||
  [[ "$digest_hex" == *[!0-9a-f]* ]]; then
  printf 'ECR returned an invalid image digest: %s\n' "$digest" >&2
  exit 1
fi

printf '\nUse this immutable reference:\n'
printf 'export DOWNLOADER_IMAGE=%q\n' "${registry}/${repository}@${digest}"
