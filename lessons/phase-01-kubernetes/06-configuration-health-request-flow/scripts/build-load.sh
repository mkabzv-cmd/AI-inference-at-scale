#!/usr/bin/env bash
set -euo pipefail

image="lesson06/health-app:0.1.0"
context="$(kubectl config current-context 2>/dev/null || true)"

if [[ "$context" == kind-* ]]; then
  command -v docker >/dev/null 2>&1 || {
    printf 'ERROR: docker is required to build for kind.\n' >&2
    exit 1
  }
  command -v kind >/dev/null 2>&1 || {
    printf 'ERROR: kind is required for a kind context.\n' >&2
    exit 1
  }
  cluster="${context#kind-}"
  docker build --tag "$image" .
  kind load docker-image "$image" --name "$cluster"
elif [[ "$context" == minikube* ]]; then
  command -v minikube >/dev/null 2>&1 || {
    printf 'ERROR: minikube is required for a Minikube context.\n' >&2
    exit 1
  }
  profile="${MINIKUBE_PROFILE:-$context}"
  minikube image build --profile "$profile" --tag "$image" .
else
  printf 'Current context is %s.\n' "${context:-<none>}"
  printf 'Build %s into the container runtime visible to this cluster.\n' "$image"
  printf 'For Docker Desktop Kubernetes, this is usually:\n'
  printf '  docker build --tag %s .\n' "$image"
  exit 2
fi

printf 'image ready in cluster runtime: %s\n' "$image"
