#!/usr/bin/env bash
set -euo pipefail

required=(kubectl helm curl docker python3)
missing=0

for command_name in "${required[@]}"; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf 'missing required command: %s\n' "$command_name" >&2
    missing=1
  fi
done
[[ "$missing" -eq 0 ]] || exit 1

printf 'kubectl context: %s\n' "$(kubectl config current-context)"
kubectl cluster-info
kubectl auth can-i create deployments.apps --namespace packaging-lab
kubectl auth can-i create services --namespace packaging-lab
helm version --short
docker version --format 'docker client={{.Client.Version}}'

helm lint chart/lesson-service
helm template course chart/lesson-service \
  --namespace packaging-lab >/dev/null
printf 'chart lint and render: OK\n'
