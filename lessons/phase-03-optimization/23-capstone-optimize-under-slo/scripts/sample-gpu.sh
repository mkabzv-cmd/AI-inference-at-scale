#!/usr/bin/env bash
set -euo pipefail

candidate="${1:?usage: $0 CANDIDATE_ID}"
samples="${SAMPLES:-90}"
interval="${INTERVAL_SECONDS:-2}"
if [[ ! "$candidate" =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] ||
  (( ${#candidate} > 63 )); then
  printf 'candidate ID must be a Kubernetes-safe name\n' >&2
  exit 2
fi
if [[ ! "$samples" =~ ^[0-9]+$ ]] || (( samples < 1 || samples > 600 )); then
  printf 'SAMPLES must be an integer from 1 through 600\n' >&2
  exit 2
fi
if [[ ! "$interval" =~ ^[0-9]+$ ]] || (( interval < 1 || interval > 60 )); then
  printf 'INTERVAL_SECONDS must be an integer from 1 through 60\n' >&2
  exit 2
fi
directory="artifacts/$candidate"
mkdir -p "$directory"
output="$directory/gpu-timeseries.csv"
printf '%s\n' \
  'sample,timestamp,name,driver_version,memory_total_mib,memory_used_mib,utilization_gpu_percent' \
  > "$output"
for ((index=1; index<=samples; index++)); do
  row="$(
    kubectl exec -n oms-lesson-23 deployment/vllm -- \
      nvidia-smi \
      --query-gpu=timestamp,name,driver_version,memory.total,memory.used,utilization.gpu \
      --format=csv,noheader,nounits
  )"
  printf '%s,%s\n' "$index" "$row" >> "$output"
  sleep "$interval"
done
echo "wrote $output"
