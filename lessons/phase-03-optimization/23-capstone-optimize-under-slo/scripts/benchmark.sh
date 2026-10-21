#!/usr/bin/env bash
set -euo pipefail

: "${VLLM_IMAGE:?set immutable engine image for evidence}"
: "${VLLM_EXPECTED_VERSION:=0.28.0}"
candidate="${1:?usage: $0 CANDIDATE_ID}"
if [[ ! "$candidate" =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] ||
  (( ${#candidate} > 63 )); then
  printf 'candidate ID must be a Kubernetes-safe name\n' >&2
  exit 2
fi
python3 - "$candidate" <<'PY'
import json
import sys
from pathlib import Path

candidate = sys.argv[1]
config = json.loads(Path("configs/candidates.json").read_text())
known = {str(item["id"]) for item in config["candidates"]}
if candidate not in known:
    raise SystemExit(f"unknown candidate {candidate!r}; choose {sorted(known)}")
PY
live_version="$(
  kubectl exec -n oms-lesson-23 deployment/vllm -- \
    python -c \
    'from importlib.metadata import version; print(version("vllm"))'
)"
if [[ "$live_version" != "$VLLM_EXPECTED_VERSION" ]]; then
  printf 'running vLLM version %s differs from expected %s\n' \
    "$live_version" "$VLLM_EXPECTED_VERSION" >&2
  exit 1
fi
mkdir -p "artifacts/$candidate"
python3 src/benchmark_endpoint.py \
  --workload configs/workload.json \
  --base-url "${BASE_URL:-http://127.0.0.1:8000}" \
  --model oms-model \
  --engine-image-digest "$VLLM_IMAGE" \
  --engine-version "$live_version" \
  --candidate-id "$candidate" \
  --output "artifacts/$candidate/results.json"
kubectl exec -n oms-lesson-23 deployment/vllm -- \
  nvidia-smi \
  --query-gpu=timestamp,name,driver_version,memory.total,memory.used,utilization.gpu \
  --format=csv |
  tee "artifacts/$candidate/gpu-after.csv"
