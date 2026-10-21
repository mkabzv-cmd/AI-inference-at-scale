#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:?set LAB_NAMESPACE}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/../../common/scripts/assert-eks-target.sh"
version="${KUBERAY_CHART_VERSION:-1.7.0}"
if [[ "$version" != "1.7.0" ]]; then
  printf 'this draft is pinned to KUBERAY_CHART_VERSION=1.7.0\n' >&2
  exit 2
fi
if [[ "${CONFIRM_KUBERAY_INSTALL:-}" != "kuberay-operator-${version}" ]]; then
  printf '%s\n' \
    "set CONFIRM_KUBERAY_INSTALL=kuberay-operator-${version} after review" >&2
  exit 3
fi
: "${KUBERAY_OPERATOR_IMAGE:?set a reviewed repository:tag@sha256 digest}"
if [[ ! "$KUBERAY_OPERATOR_IMAGE" =~ ^[A-Za-z0-9][A-Za-z0-9./_-]*:[A-Za-z0-9._-]+@sha256:[0-9a-f]{64}$ ]]; then
  printf '%s\n' \
    'KUBERAY_OPERATOR_IMAGE must be repository:tag@sha256:<64 lowercase hex>' >&2
  exit 2
fi
image_before_digest="${KUBERAY_OPERATOR_IMAGE%@sha256:*}"
image_repository="${image_before_digest%:*}"
image_tag_digest="${image_before_digest##*:}@${KUBERAY_OPERATOR_IMAGE##*@}"
for command_name in helm kubectl; do
  command -v "$command_name" >/dev/null 2>&1 || {
    printf 'missing command: %s\n' "$command_name" >&2
    exit 2
  }
done
for permission in \
  'create customresourcedefinitions.apiextensions.k8s.io' \
  'create clusterroles.rbac.authorization.k8s.io' \
  'create clusterrolebindings.rbac.authorization.k8s.io'; do
  verb="${permission%% *}"
  resource="${permission#* }"
  if ! kubectl auth can-i "$verb" "$resource" | grep -qx yes; then
    printf 'missing cluster-wide permission: %s %s\n' \
      "$verb" "$resource" >&2
    exit 1
  fi
done

mkdir -p artifacts/chart
helm repo add kuberay https://ray-project.github.io/kuberay-helm/ \
  --force-update
helm repo update kuberay
helm pull kuberay/kuberay-operator \
  --version "$version" \
  --destination artifacts/chart
helm template kuberay-operator \
  "artifacts/chart/kuberay-operator-${version}.tgz" \
  --namespace kuberay-system \
  --set-string "image.repository=${image_repository}" \
  --set-string "image.tag=${image_tag_digest}" \
  >artifacts/chart/operator-rendered.yaml

printf 'Digest-pinned operator image references:\n'
grep -E '^[[:space:]]*image:' artifacts/chart/operator-rendered.yaml |
  sort -u
unsafe_images="$(
  grep -E '^[[:space:]]*image:' artifacts/chart/operator-rendered.yaml |
    sed -E 's/^[[:space:]]*image:[[:space:]]*"?([^"]+)"?[[:space:]]*$/\1/' |
    grep -Ev '@sha256:[0-9a-f]{64}$' || true
)"
if [[ -n "$unsafe_images" ]]; then
  printf 'refusing mutable operator image references:\n%s\n' \
    "$unsafe_images" >&2
  exit 1
fi
grep -Fq "$KUBERAY_OPERATOR_IMAGE" artifacts/chart/operator-rendered.yaml || {
  printf 'rendered chart does not contain the approved operator digest\n' >&2
  exit 1
}

helm upgrade --install kuberay-operator \
  "artifacts/chart/kuberay-operator-${version}.tgz" \
  --namespace kuberay-system \
  --create-namespace \
  --set-string "image.repository=${image_repository}" \
  --set-string "image.tag=${image_tag_digest}" \
  --wait \
  --timeout 5m
kubectl -n kuberay-system get pods -o jsonpath=\
'{range .items[*]}{.metadata.name}{"\t"}{range .status.containerStatuses[*]}{.image}{"\t"}{.imageID}{"\n"}{end}{end}' \
  | tee artifacts/chart/operator-image-ids.txt
