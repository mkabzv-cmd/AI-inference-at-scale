#!/usr/bin/env bash
set -euo pipefail

command -v kubectl >/dev/null 2>&1 || {
  printf 'ERROR: kubectl is not installed or not on PATH.\n' >&2
  exit 1
}

printf 'kubectl client: '
kubectl version --client

context="$(kubectl config current-context 2>/dev/null || true)"
if [[ -z "$context" ]]; then
  printf 'ERROR: kubectl has no current context.\n' >&2
  exit 1
fi

printf 'current context: %s\n' "$context"
if [[ "$context" != "kind-llm-lab" &&
  "${ALLOW_NON_LAB_CONTEXT:-0}" != "1" ]]; then
  printf 'ERROR: expected context kind-llm-lab; refusing context %s.\n' \
    "$context" >&2
  printf '%s\n' \
    'For another verified disposable cluster, rerun with ALLOW_NON_LAB_CONTEXT=1.' >&2
  exit 1
fi

kubectl cluster-info >/dev/null
kubectl wait --for=condition=Ready node --all --timeout=120s
kubectl get nodes -o wide

command -v curl >/dev/null 2>&1 || {
  printf 'ERROR: curl is required for the HTTP checks.\n' >&2
  exit 1
}

printf 'preflight passed\n'
