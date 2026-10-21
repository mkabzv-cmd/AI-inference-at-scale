#!/usr/bin/env bash
set -euo pipefail

lesson_namespace="model-storage-lab"
expected_part_of="open-model-course"
expected_lesson="08"

assert_eks_target() {
  : "${AWS_REGION:?set AWS_REGION to the intended EKS region}"
  : "${EKS_CLUSTER:?set EKS_CLUSTER to the intended lab cluster}"

  for command_name in aws kubectl; do
    command -v "$command_name" >/dev/null 2>&1 || {
      printf 'missing required command: %s\n' "$command_name" >&2
      return 1
    }
  done

  local expected_server
  local active_server
  local context
  expected_server="$(
    aws eks describe-cluster \
      --region "$AWS_REGION" \
      --name "$EKS_CLUSTER" \
      --query 'cluster.endpoint' \
      --output text
  )"
  active_server="$(
    kubectl config view --minify \
      -o jsonpath='{.clusters[0].cluster.server}'
  )"
  context="$(kubectl config current-context)"

  if [[ -z "$expected_server" || "$expected_server" == "None" ]]; then
    printf 'could not resolve the EKS endpoint for %s\n' "$EKS_CLUSTER" >&2
    return 1
  fi
  if [[ -z "$active_server" || "$active_server" != "$expected_server" ]]; then
    printf 'refusing Kubernetes target mismatch\n' >&2
    printf '  context:  %s\n' "$context" >&2
    printf '  current:  %s\n' "${active_server:-<none>}" >&2
    printf '  expected: %s\n' "$expected_server" >&2
    return 1
  fi
  printf 'verified EKS target: %s (%s)\n' "$EKS_CLUSTER" "$context"
}

assert_namespace_owned_or_absent() {
  local found
  local part_of
  local lesson
  found="$(
    kubectl get namespace "$lesson_namespace" \
      --ignore-not-found \
      -o name
  )"
  if [[ -z "$found" ]]; then
    printf 'lesson namespace is absent: %s\n' "$lesson_namespace"
    return 0
  fi

  part_of="$(
    kubectl get namespace "$lesson_namespace" \
      -o jsonpath='{.metadata.labels.app\.kubernetes\.io/part-of}'
  )"
  lesson="$(
    kubectl get namespace "$lesson_namespace" \
      -o jsonpath='{.metadata.labels.lesson\.open-model-course/id}'
  )"
  if [[ "$part_of" != "$expected_part_of" || "$lesson" != "$expected_lesson" ]]; then
    printf 'refusing namespace %s with unexpected ownership labels\n' \
      "$lesson_namespace" >&2
    printf '  part-of=%s lesson=%s\n' \
      "${part_of:-<missing>}" "${lesson:-<missing>}" >&2
    return 1
  fi
  printf 'verified lesson namespace ownership: %s\n' "$lesson_namespace"
}

assert_storageclass_owned_or_absent() {
  local name="$1"
  local found
  local lesson
  found="$(kubectl get storageclass "$name" --ignore-not-found -o name)"
  if [[ -z "$found" ]]; then
    printf 'lesson StorageClass is absent: %s\n' "$name"
    return 0
  fi
  lesson="$(
    kubectl get storageclass "$name" \
      -o jsonpath='{.metadata.labels.lesson\.open-model-course/id}'
  )"
  if [[ "$lesson" != "$expected_lesson" ]]; then
    printf 'refusing StorageClass %s with lesson label %s\n' \
      "$name" "${lesson:-<missing>}" >&2
    return 1
  fi
  printf 'verified lesson StorageClass ownership: %s\n' "$name"
}

if [[ "${BASH_SOURCE[0]:-}" == "$0" ]]; then
  assert_eks_target
  assert_namespace_owned_or_absent
  assert_storageclass_owned_or_absent model-cache-gp3
  assert_storageclass_owned_or_absent model-cache-gp3-auto
  printf 'Lesson 08 target checks passed.\n'
fi
