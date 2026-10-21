#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION}"
: "${ECR_REPOSITORY:?Set ECR_REPOSITORY}"

state_file="$(mktemp)"
error_file="$(mktemp)"
cleanup_files() {
  rm -f -- "$state_file" "$error_file"
}
trap cleanup_files EXIT

if aws ecr describe-repositories \
  --region "$AWS_REGION" \
  --repository-names "$ECR_REPOSITORY" \
  --query 'repositories[0].[repositoryName,imageTagMutability,imageScanningConfiguration.scanOnPush]' \
  --output text >"$state_file" 2>"$error_file"; then
  read -r repository_name mutability scan_on_push <"$state_file"
  printf 'ECR repository already exists; no change made.\n'
  printf 'repository=%s tag_mutability=%s scan_on_push=%s\n' \
    "$repository_name" "$mutability" "$scan_on_push"
  if [[ "$mutability" != "IMMUTABLE" || "$scan_on_push" != "True" ]]; then
    printf '%s\n' \
      '[fail] use a dedicated repository with IMMUTABLE tags and scan-on-push enabled' >&2
    exit 1
  fi
  exit 0
fi

if ! grep -q 'RepositoryNotFoundException' "$error_file"; then
  printf 'Unable to inspect ECR repository; refusing to treat the error as absence.\n' >&2
  cat "$error_file" >&2
  exit 1
fi

if [[ "${I_UNDERSTAND_ECR_CHANGES:-no}" != "yes" ]]; then
  printf 'Repository is absent. Re-run with I_UNDERSTAND_ECR_CHANGES=yes to create it.\n' >&2
  exit 3
fi
if [[ "${CONFIRM_ECR_REPOSITORY:-}" != "$ECR_REPOSITORY" ]]; then
  printf 'Set CONFIRM_ECR_REPOSITORY to the exact repository name: %s\n' \
    "$ECR_REPOSITORY" >&2
  exit 3
fi

aws ecr create-repository \
  --region "$AWS_REGION" \
  --repository-name "$ECR_REPOSITORY" \
  --image-tag-mutability IMMUTABLE \
  --image-scanning-configuration scanOnPush=true \
  --query 'repository.[repositoryName,repositoryUri,imageTagMutability]' \
  --output table
