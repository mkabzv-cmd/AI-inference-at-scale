#!/usr/bin/env bash
set -euo pipefail

namespace="${LAB_NAMESPACE:-one-gpu-api}"
release="${HELM_RELEASE:-one-gpu}"
mkdir -p artifacts

set +e
helm upgrade "$release" chart/one-gpu-api \
  --namespace "$namespace" \
  --reuse-values \
  --set-string probes.readiness.path=/health/not-a-real-endpoint \
  --atomic \
  --timeout 2m \
  >artifacts/failure-upgrade.txt 2>&1
status=$?
set -e

printf 'bad upgrade exit=%s (nonzero is expected)\n' "$status"
helm history "$release" -n "$namespace" |
  tee artifacts/helm-history-after-failure.txt
kubectl -n "$namespace" get pods,endpoints -o wide |
  tee artifacts/state-after-failure.txt

if [[ "$status" -eq 0 ]]; then
  printf 'expected the bad readiness rollout to fail\n' >&2
  exit 1
fi
printf 'atomic rollback requested; run test-api.sh to verify behavior\n'
