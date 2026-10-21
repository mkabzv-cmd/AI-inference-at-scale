#!/usr/bin/env bash
set -euo pipefail

: "${IMAGE_REPOSITORY:?set IMAGE_REPOSITORY}"
: "${IMAGE_DIGEST:?set IMAGE_DIGEST, including sha256:}"

namespace="${LAB_NAMESPACE:-packaging-lab}"
release="${HELM_RELEASE:-course}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/assert-target.sh"
assert_safe_target
assert_safe_release_name
ensure_owned_namespace

helm upgrade --install "$release" chart/lesson-service \
  --namespace "$namespace" \
  --set-string image.repository="$IMAGE_REPOSITORY" \
  --set-string image.digest="$IMAGE_DIGEST" \
  --wait \
  --timeout 3m

kubectl -n "$namespace" rollout status \
  deployment \
  --selector "app.kubernetes.io/instance=${release}" \
  --timeout=2m
