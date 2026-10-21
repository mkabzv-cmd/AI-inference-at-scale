#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION}"
: "${EKS_CLUSTER_NAME:?Set EKS_CLUSTER_NAME}"
: "${GPU_NODEGROUP_NAME:?Set GPU_NODEGROUP_NAME}"
: "${LAB_NAMESPACE:?Set LAB_NAMESPACE}"

if [[ "$#" -ne 1 || ! "$1" =~ ^(up|down)$ ]]; then
  printf 'Usage: %s up|down\n' "$0" >&2
  exit 2
fi
direction="$1"

if [[ "${CONFIRM_GPU_NODEGROUP:-}" != "$GPU_NODEGROUP_NAME" ]]; then
  printf 'Set CONFIRM_GPU_NODEGROUP to the exact target: %s\n' \
    "$GPU_NODEGROUP_NAME" >&2
  exit 3
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
lesson_dir="$(cd "$script_dir/.." && pwd)"
source "$script_dir/assert-target.sh"
assert_safe_namespace_name
assert_kube_context_matches_cluster

mkdir -p "$lesson_dir/.lab"
baseline_file="$lesson_dir/.lab/nodegroup-before.json"
account_id="$(aws sts get-caller-identity --query Account --output text)"
post_scale_verification_failed=0

read_current_scaling() {
  aws eks describe-nodegroup \
    --region "$AWS_REGION" \
    --cluster-name "$EKS_CLUSTER_NAME" \
    --nodegroup-name "$GPU_NODEGROUP_NAME" \
    --query 'nodegroup.[status,scalingConfig.desiredSize,scalingConfig.minSize,scalingConfig.maxSize]' \
    --output text
}

read_baseline() {
  python3 -c '
import json
import sys

record = json.load(open(sys.argv[1], encoding="utf-8"))
scaling = record["scaling"]
print(
    record["account_id"],
    record["region"],
    record["cluster"],
    record["nodegroup"],
    scaling["desired"],
    scaling["minimum"],
    scaling["maximum"],
)
' "$baseline_file"
}

validate_saved_scaling() {
  if [[ ! "$saved_desired" =~ ^[0-9]+$ ||
    ! "$saved_minimum" =~ ^[0-9]+$ ||
    ! "$saved_maximum" =~ ^[0-9]+$ ]]; then
    printf 'Saved baseline has non-integer scaling values: %s\n' \
      "$baseline_file" >&2
    return 1
  fi
  if [[ "$saved_desired" != "0" || "$saved_minimum" != "0" ]] ||
    (( saved_maximum < 1 )); then
    printf '%s\n' \
      'Saved baseline is not an idle min=0 desired=0 lab configuration.' >&2
    printf 'Refusing to apply a corrupted or non-idle baseline.\n' >&2
    return 1
  fi
}

wait_for_update() {
  local update_id="$1"
  local update_status
  local deadline=$((SECONDS + 900))

  while true; do
    update_status="$(
      aws eks describe-update \
        --region "$AWS_REGION" \
        --name "$EKS_CLUSTER_NAME" \
        --nodegroup-name "$GPU_NODEGROUP_NAME" \
        --update-id "$update_id" \
        --query 'update.status' \
        --output text
    )"
    case "$update_status" in
      Successful)
        break
        ;;
      Failed | Cancelled)
        printf 'EKS scaling update %s ended with status %s\n' \
          "$update_id" "$update_status" >&2
        aws eks describe-update \
          --region "$AWS_REGION" \
          --name "$EKS_CLUSTER_NAME" \
          --nodegroup-name "$GPU_NODEGROUP_NAME" \
          --update-id "$update_id" \
          --output json >&2
        return 1
        ;;
      InProgress)
        ;;
      *)
        printf 'Unexpected EKS update status: %s\n' "$update_status" >&2
        return 1
        ;;
    esac
    if (( SECONDS >= deadline )); then
      printf 'Timed out waiting for EKS update %s\n' "$update_id" >&2
      return 1
    fi
    sleep 5
  done

  aws eks wait nodegroup-active \
    --region "$AWS_REGION" \
    --cluster-name "$EKS_CLUSTER_NAME" \
    --nodegroup-name "$GPU_NODEGROUP_NAME"
}

apply_scaling() {
  local target_minimum="$1"
  local target_maximum="$2"
  local target_desired="$3"
  local update_id

  read -r status desired minimum maximum < <(read_current_scaling)
  if [[ "$status" != "ACTIVE" ]]; then
    printf 'Node group must be ACTIVE before changing scaling; found %s\n' \
      "$status" >&2
    return 1
  fi
  if [[ "$desired" == "$target_desired" &&
    "$minimum" == "$target_minimum" &&
    "$maximum" == "$target_maximum" ]]; then
    printf 'Scaling already matches min=%s max=%s desired=%s\n' \
      "$target_minimum" "$target_maximum" "$target_desired"
    return 0
  fi

  update_id="$(
    aws eks update-nodegroup-config \
      --region "$AWS_REGION" \
      --cluster-name "$EKS_CLUSTER_NAME" \
      --nodegroup-name "$GPU_NODEGROUP_NAME" \
      --scaling-config \
      "minSize=${target_minimum},maxSize=${target_maximum},desiredSize=${target_desired}" \
      --query 'update.id' \
      --output text
  )"
  if [[ -z "$update_id" || "$update_id" == "None" ]]; then
    printf 'EKS did not return a scaling update ID\n' >&2
    return 1
  fi
  printf 'Started EKS update: %s\n' "$update_id"
  wait_for_update "$update_id"
}

read -r status desired minimum maximum < <(read_current_scaling)
printf 'Before: status=%s desired=%s min=%s max=%s\n' \
  "$status" "$desired" "$minimum" "$maximum"
if [[ "$status" != "ACTIVE" ]]; then
  printf 'Node group must be ACTIVE before changing scaling.\n' >&2
  exit 1
fi

if [[ "$direction" == "up" ]]; then
  assert_namespace_owned_or_absent
  if [[ "${I_UNDERSTAND_GPU_COSTS:-no}" != "yes" ]]; then
    printf 'Re-run with I_UNDERSTAND_GPU_COSTS=yes after reviewing cost and target.\n' >&2
    exit 3
  fi
  if (( maximum < 1 )); then
    printf 'Configured node-group maximum is less than one.\n' >&2
    exit 1
  fi

  if [[ -f "$baseline_file" ]]; then
    read -r saved_account saved_region saved_cluster saved_nodegroup \
      saved_desired saved_minimum saved_maximum < <(read_baseline)
    if [[ "$saved_account" != "$account_id" ||
      "$saved_region" != "$AWS_REGION" ||
      "$saved_cluster" != "$EKS_CLUSTER_NAME" ||
      "$saved_nodegroup" != "$GPU_NODEGROUP_NAME" ]]; then
      printf 'Existing baseline belongs to a different AWS target: %s\n' \
        "$baseline_file" >&2
      exit 1
    fi
    validate_saved_scaling
    if ! {
      [[ "$desired" == "$saved_desired" &&
        "$minimum" == "$saved_minimum" &&
        "$maximum" == "$saved_maximum" ]] ||
        [[ "$desired" == "1" && "$minimum" == "0" && "$maximum" == "1" ]]
    }; then
      printf 'Current scaling differs from both the saved baseline and lab cap.\n' >&2
      printf 'Refusing to overwrite baseline or guess ownership.\n' >&2
      exit 1
    fi
    printf 'Reusing matching baseline: %s\n' "$baseline_file"
  else
    if [[ "$desired" != "0" || "$minimum" != "0" ]]; then
      printf '%s\n' \
        'Refusing scale-up: a new lab must start with min=0 and desired=0.' >&2
      printf '%s\n' \
        'Investigate who owns the existing capacity; do not claim it as this lab.' >&2
      exit 1
    fi
    python3 - "$baseline_file" "$account_id" "$AWS_REGION" \
      "$EKS_CLUSTER_NAME" "$GPU_NODEGROUP_NAME" \
      "$desired" "$minimum" "$maximum" <<'PY'
import json
import sys
from pathlib import Path

(
    path,
    account_id,
    region,
    cluster,
    nodegroup,
    desired,
    minimum,
    maximum,
) = sys.argv[1:]
record = {
    "schema_version": 1,
    "account_id": account_id,
    "region": region,
    "cluster": cluster,
    "nodegroup": nodegroup,
    "scaling": {
        "desired": int(desired),
        "minimum": int(minimum),
        "maximum": int(maximum),
    },
}
Path(path).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
PY
    printf 'Saved starting scaling config: %s\n' "$baseline_file"
  fi

  apply_scaling 0 1 1
  printf 'Waiting for one Kubernetes node to register...\n'
  deadline=$((SECONDS + 900))
  while true; do
    nodes="$(
      kubectl get nodes \
        -l "eks.amazonaws.com/nodegroup=$GPU_NODEGROUP_NAME" \
        -o name
    )"
    if [[ -n "$nodes" ]]; then
      break
    fi
    if (( SECONDS >= deadline )); then
      printf 'Timed out waiting for a node to register.\n' >&2
      exit 1
    fi
    sleep 10
  done
  kubectl wait \
    --for=condition=Ready \
    node \
    -l "eks.amazonaws.com/nodegroup=$GPU_NODEGROUP_NAME" \
    --timeout=10m
else
  if namespace="$(
    kubectl get namespace "$LAB_NAMESPACE" \
      --ignore-not-found \
      -o name
  )"; then
    if [[ -n "$namespace" ]]; then
      printf 'Warning: namespace still exists; scaling down for cost safety: %s\n' \
        "$LAB_NAMESPACE" >&2
      post_scale_verification_failed=1
    fi
  else
    printf '%s\n' \
      'Warning: could not inspect the namespace; scaling down for cost safety.' >&2
    post_scale_verification_failed=1
  fi
  if [[ ! -f "$baseline_file" ]]; then
    printf 'Missing saved baseline: %s\n' "$baseline_file" >&2
    printf '%s\n' \
      'Refusing to guess a scale-down target. Inspect the node group manually.' >&2
    exit 1
  fi
  read -r saved_account saved_region saved_cluster saved_nodegroup \
    saved_desired saved_minimum saved_maximum < <(read_baseline)
  if [[ "$saved_account" != "$account_id" ||
    "$saved_region" != "$AWS_REGION" ||
    "$saved_cluster" != "$EKS_CLUSTER_NAME" ||
    "$saved_nodegroup" != "$GPU_NODEGROUP_NAME" ]]; then
    printf 'Saved baseline belongs to a different AWS target: %s\n' \
      "$baseline_file" >&2
    exit 1
  fi
  validate_saved_scaling

  apply_scaling "$saved_minimum" "$saved_maximum" "$saved_desired"
  if [[ "$saved_desired" == "0" ]]; then
    printf 'Waiting for lesson node objects to disappear...\n'
    deadline=$((SECONDS + 900))
    while true; do
      if ! nodes="$(
        kubectl get nodes \
          -l "eks.amazonaws.com/nodegroup=$GPU_NODEGROUP_NAME" \
          -o name
      )"; then
        printf '%s\n' \
          'Warning: scaling was restored, but Kubernetes node removal could not be verified.' >&2
        post_scale_verification_failed=1
        break
      fi
      if [[ -z "$nodes" ]]; then
        break
      fi
      if (( SECONDS >= deadline )); then
        printf 'Timed out waiting for GPU node objects to disappear.\n' >&2
        exit 1
      fi
      sleep 10
    done
  fi
fi

aws eks describe-nodegroup \
  --region "$AWS_REGION" \
  --cluster-name "$EKS_CLUSTER_NAME" \
  --nodegroup-name "$GPU_NODEGROUP_NAME" \
  --query 'nodegroup.[status,scalingConfig]' \
  --output json

if (( post_scale_verification_failed > 0 )); then
  printf '%s\n' \
    'Node-group scaling was restored, but workload/node cleanup still needs verification.' >&2
  exit 1
fi
