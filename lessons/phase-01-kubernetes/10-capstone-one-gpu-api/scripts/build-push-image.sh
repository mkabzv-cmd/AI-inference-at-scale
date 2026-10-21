#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:?set AWS_REGION}"
: "${AWS_ACCOUNT_ID:?set AWS_ACCOUNT_ID}"
: "${BASE_IMAGE:?set BASE_IMAGE to pytorch/pytorch@sha256:...}"

actual_account_id="$(
  aws sts get-caller-identity --query Account --output text
)"
if [[ "$actual_account_id" != "$AWS_ACCOUNT_ID" ]]; then
  printf 'AWS_ACCOUNT_ID=%s but active credentials use %s\n' \
    "$AWS_ACCOUNT_ID" "$actual_account_id" >&2
  exit 1
fi

base_digest="${BASE_IMAGE##*@sha256:}"
if [[ "$BASE_IMAGE" != *@sha256:* ]] ||
  [[ "${#base_digest}" -ne 64 ]] ||
  [[ "$base_digest" == *[!0-9a-f]* ]]; then
  printf 'BASE_IMAGE must end in @sha256:<64 lowercase hex characters>\n' >&2
  exit 1
fi

repository="${ECR_REPOSITORY:-open-model-course/one-gpu-api}"
tag="${IMAGE_TAG:-lesson-10-v1}"
registry="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
image="${registry}/${repository}:${tag}"

if repository_state="$(
  aws ecr describe-repositories \
    --region "$AWS_REGION" \
    --repository-names "$repository" \
    --query 'repositories[0].[imageTagMutability,imageScanningConfiguration.scanOnPush]' \
    --output text 2>&1
)"; then
  read -r tag_mutability scan_on_push <<<"$repository_state"
  if [[ "$tag_mutability" != "IMMUTABLE" || "$scan_on_push" != "True" ]]; then
    printf 'ECR repository must use IMMUTABLE tags and scan-on-push: %s\n' \
      "$repository" >&2
    exit 1
  fi
else
  if [[ "$repository_state" != *RepositoryNotFoundException* ]]; then
    printf 'could not inspect ECR repository %s:\n%s\n' \
      "$repository" "$repository_state" >&2
    exit 1
  fi
  if [[ "${I_UNDERSTAND_ECR_CHANGES:-no}" != "yes" ||
    "${CONFIRM_ECR_REPOSITORY:-}" != "$repository" ]]; then
    printf 'repository is absent; to create it, set both:\n' >&2
    printf '  I_UNDERSTAND_ECR_CHANGES=yes\n' >&2
    printf '  CONFIRM_ECR_REPOSITORY=%s\n' "$repository" >&2
    exit 3
  fi
  aws ecr create-repository \
    --region "$AWS_REGION" \
    --repository-name "$repository" \
    --image-tag-mutability IMMUTABLE \
    --image-scanning-configuration scanOnPush=true >/dev/null
fi

aws ecr get-login-password --region "$AWS_REGION" |
  docker login --username AWS --password-stdin "$registry"
docker build \
  --platform linux/amd64 \
  --build-arg "BASE_IMAGE=${BASE_IMAGE}" \
  --tag "$image" \
  app
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

printf 'export IMAGE_REPOSITORY=%q\n' "${registry}/${repository}"
printf 'export IMAGE_DIGEST=%q\n' "$digest"
printf 'export BASE_IMAGE_USED=%q\n' "$BASE_IMAGE"
