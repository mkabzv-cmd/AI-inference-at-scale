#!/usr/bin/env bash
set -euo pipefail

: "${ALLOW_LESSON_39_ROLLBACK:?Set ALLOW_LESSON_39_ROLLBACK=yes}"
: "${ROLLBACK_MANIFEST:?Set the path to the previously verified immutable manifest}"
if [[ "$ALLOW_LESSON_39_ROLLBACK" != "yes" ]]; then
  printf 'Refusing: ALLOW_LESSON_39_ROLLBACK must equal yes\n' >&2
  exit 1
fi
test -f "$ROLLBACK_MANIFEST"
grep -Eq 'image: [^[:space:]]+@sha256:[0-9a-f]{64}' "$ROLLBACK_MANIFEST"
if grep -Eq \
  'kind:[[:space:]]*Ingress|type:[[:space:]]*(LoadBalancer|NodePort|ExternalName)|externalIPs:|host(Network|Port):[[:space:]]*(true|[0-9]+)|nodePort:|privileged:[[:space:]]*true' \
  "$ROLLBACK_MANIFEST"; then
  printf 'Refusing a rollback manifest with public or privileged exposure\n' >&2
  exit 1
fi
kubectl apply -f "$ROLLBACK_MANIFEST"
kubectl -n oms-l39 rollout status deployment/adapted-model --timeout=20m
printf 'Rollback manifest applied; rerun health, acceptance, and provenance checks\n'
