#!/usr/bin/env bash
set -euo pipefail

expected_part_of="open-model-course"
expected_lesson="09"

lesson_namespace() {
  printf '%s\n' "${LAB_NAMESPACE:-packaging-lab}"
}

assert_safe_namespace_name() {
  local namespace
  namespace="$(lesson_namespace)"
  if [[ "$namespace" == "packaging-lab" ]]; then
    return 0
  fi
  if (( ${#namespace} > 63 )) ||
    [[ ! "$namespace" =~ ^open-models-[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]]; then
    printf 'custom LAB_NAMESPACE must be a DNS label beginning with open-models-\n' >&2
    return 1
  fi
  if [[ "${CONFIRM_LAB_NAMESPACE:-}" != "$namespace" ]]; then
    printf 'set CONFIRM_LAB_NAMESPACE to the exact custom namespace: %s\n' \
      "$namespace" >&2
    return 1
  fi
}

assert_safe_target() {
  assert_safe_namespace_name
  command -v kubectl >/dev/null 2>&1 || {
    printf 'missing required command: kubectl\n' >&2
    return 1
  }

  local context
  context="$(kubectl config current-context 2>/dev/null || true)"
  if [[ -z "$context" ]]; then
    printf 'kubectl has no current context\n' >&2
    return 1
  fi

  if [[ "$context" == "kind-llm-lab" ]]; then
    printf 'verified course local Kubernetes context: %s\n' "$context"
    return 0
  fi
  case "$context" in
    kind-* | minikube* | docker-desktop)
      if [[ "${ALLOW_NON_COURSE_LOCAL_CONTEXT:-0}" != "1" ]]; then
        printf 'refusing non-course local context: %s\n' "$context" >&2
        printf '%s\n' \
          'After verifying it is disposable, set ALLOW_NON_COURSE_LOCAL_CONTEXT=1.' >&2
        return 1
      fi
      printf 'verified explicit opt-in for local context: %s\n' "$context"
      return 0
      ;;
  esac

  : "${AWS_REGION:?set AWS_REGION for the intended EKS cluster}"
  : "${EKS_CLUSTER:?set EKS_CLUSTER for the intended EKS cluster}"
  command -v aws >/dev/null 2>&1 || {
    printf 'aws is required when the current context is not a known local cluster\n' >&2
    return 1
  }

  local expected_server
  local active_server
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
  if [[ -z "$expected_server" || "$expected_server" == "None" ||
    -z "$active_server" || "$active_server" != "$expected_server" ]]; then
    printf 'refusing Kubernetes target mismatch\n' >&2
    printf '  context:  %s\n' "$context" >&2
    printf '  current:  %s\n' "${active_server:-<none>}" >&2
    printf '  expected: %s\n' "${expected_server:-<none>}" >&2
    return 1
  fi
  printf 'verified EKS target: %s (%s)\n' "$EKS_CLUSTER" "$context"
}

assert_namespace_owned_or_absent() {
  local namespace
  local found
  local part_of
  local lesson
  namespace="$(lesson_namespace)"
  found="$(kubectl get namespace "$namespace" --ignore-not-found -o name)"
  if [[ -z "$found" ]]; then
    printf 'lesson namespace is absent: %s\n' "$namespace"
    return 0
  fi
  part_of="$(
    kubectl get namespace "$namespace" \
      -o jsonpath='{.metadata.labels.app\.kubernetes\.io/part-of}'
  )"
  lesson="$(
    kubectl get namespace "$namespace" \
      -o jsonpath='{.metadata.labels.lesson\.open-model-course/id}'
  )"
  if [[ "$part_of" != "$expected_part_of" || "$lesson" != "$expected_lesson" ]]; then
    printf 'refusing namespace %s with unexpected ownership labels\n' \
      "$namespace" >&2
    printf '  part-of=%s lesson=%s\n' \
      "${part_of:-<missing>}" "${lesson:-<missing>}" >&2
    return 1
  fi
  printf 'verified lesson namespace ownership: %s\n' "$namespace"
}

ensure_owned_namespace() {
  local namespace
  namespace="$(lesson_namespace)"
  assert_namespace_owned_or_absent
  if ! kubectl get namespace "$namespace" >/dev/null 2>&1; then
    printf '%s\n' \
      'apiVersion: v1' \
      'kind: Namespace' \
      'metadata:' \
      "  name: ${namespace}" \
      '  labels:' \
      "    app.kubernetes.io/part-of: ${expected_part_of}" \
      "    lesson.open-model-course/id: \"${expected_lesson}\"" |
      kubectl apply -f -
  fi
  if ! kubectl get namespace "$namespace" >/dev/null 2>&1; then
    printf 'namespace creation did not produce namespace/%s\n' "$namespace" >&2
    return 1
  fi
  assert_namespace_owned_or_absent
}

assert_safe_release_name() {
  local release="${HELM_RELEASE:-course}"
  if [[ "$release" == "course" ]]; then
    return 0
  fi
  if [[ ! "$release" =~ ^course-[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ||
    "${CONFIRM_HELM_RELEASE:-}" != "$release" ]]; then
    printf 'custom HELM_RELEASE must begin course- and match CONFIRM_HELM_RELEASE\n' >&2
    return 1
  fi
}

if [[ "${BASH_SOURCE[0]:-}" == "$0" ]]; then
  assert_safe_target
  assert_namespace_owned_or_absent
  assert_safe_release_name
  printf 'Lesson 09 target checks passed.\n'
fi
