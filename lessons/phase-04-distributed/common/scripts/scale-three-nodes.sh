#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 1 || ! "$1" =~ ^(up|down)$ ]]; then
  printf 'usage: %s up|down\n' "$0" >&2
  exit 2
fi
direction="$1"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/assert-eks-target.sh"

target="${GPU_NODE_COUNT:-3}"
if [[ "$target" != "3" ]]; then
  printf '[fail] this phase requires GPU_NODE_COUNT=3, found %s\n' \
    "$target" >&2
  exit 2
fi

evidence_dir="${EVIDENCE_DIR:-artifacts}"
mkdir -p "$evidence_dir"
baseline="$evidence_dir/nodegroup-before.json"

read_scaling() {
  aws eks describe-nodegroup \
    --region "$AWS_REGION" \
    --cluster-name "$EKS_CLUSTER" \
    --nodegroup-name "$GPU_NODEGROUP" \
    --query \
    'nodegroup.[status,scalingConfig.minSize,scalingConfig.maxSize,scalingConfig.desiredSize]' \
    --output text
}

wait_for_update() {
  local update_id="$1"
  local status
  local deadline=$((SECONDS + 1200))
  while (( SECONDS < deadline )); do
    status="$(
      aws eks describe-update \
        --region "$AWS_REGION" \
        --name "$EKS_CLUSTER" \
        --nodegroup-name "$GPU_NODEGROUP" \
        --update-id "$update_id" \
        --query update.status \
        --output text
    )"
    case "$status" in
      Successful)
        return 0
        ;;
      Failed | Cancelled)
        printf '[fail] EKS update %s ended %s\n' "$update_id" "$status" >&2
        return 1
        ;;
      InProgress)
        ;;
      *)
        printf '[fail] unexpected EKS update status: %s\n' "$status" >&2
        return 1
        ;;
    esac
    sleep 5
  done
  printf '[fail] timed out waiting for EKS update %s\n' "$update_id" >&2
  return 1
}

apply_scaling() {
  local minimum="$1"
  local maximum="$2"
  local desired="$3"
  local update_id
  update_id="$(
    aws eks update-nodegroup-config \
      --region "$AWS_REGION" \
      --cluster-name "$EKS_CLUSTER" \
      --nodegroup-name "$GPU_NODEGROUP" \
      --scaling-config \
      "minSize=${minimum},maxSize=${maximum},desiredSize=${desired}" \
      --query update.id \
      --output text
  )"
  if [[ -z "$update_id" || "$update_id" == "None" ]]; then
    printf '[fail] EKS returned no update ID\n' >&2
    exit 1
  fi
  printf 'EKS update: %s\n' "$update_id"
  wait_for_update "$update_id"
  aws eks wait nodegroup-active \
    --region "$AWS_REGION" \
    --cluster-name "$EKS_CLUSTER" \
    --nodegroup-name "$GPU_NODEGROUP"
}

read -r status minimum maximum desired < <(read_scaling)
printf 'current scaling: status=%s min=%s max=%s desired=%s\n' \
  "$status" "$minimum" "$maximum" "$desired"
if [[ "$status" != "ACTIVE" ]]; then
  printf '[fail] node group must be ACTIVE\n' >&2
  exit 1
fi

if [[ "$direction" == "up" ]]; then
  if [[ "${I_UNDERSTAND_GPU_COSTS:-no}" != "yes" ]]; then
    printf '%s\n' \
      '[fail] set I_UNDERSTAND_GPU_COSTS=yes after checking current price' >&2
    exit 3
  fi
  if [[ "$minimum" != "0" || "$desired" != "0" ]]; then
    printf '%s\n' \
      '[fail] a new lab must begin with idle min=0 and desired=0 capacity' >&2
    exit 1
  fi
  if (( maximum < target )); then
    printf '[fail] node-group maximum %s is below required %s\n' \
      "$maximum" "$target" >&2
    exit 1
  fi
  if [[ -e "$baseline" ]]; then
    printf '[fail] baseline already exists: %s\n' "$baseline" >&2
    printf '%s\n' \
      'Finish or recover the previous cleanup instead of overwriting it.' >&2
    exit 1
  fi
  active_account="$(
    aws sts get-caller-identity --query Account --output text
  )"
  python3 - \
    "$baseline" \
    "$active_account" \
    "$AWS_REGION" \
    "$EKS_CLUSTER" \
    "$GPU_NODEGROUP" \
    "$minimum" \
    "$maximum" \
    "$desired" <<'PY'
import json
import os
import pathlib
import sys

(
    path_value,
    account,
    region,
    cluster,
    nodegroup,
    minimum,
    maximum,
    desired,
) = sys.argv[1:]
path = pathlib.Path(path_value)
temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
record = {
    "schema_version": 1,
    "account_id": account,
    "region": region,
    "cluster": cluster,
    "nodegroup": nodegroup,
    "scaling": {
        "minSize": int(minimum),
        "maxSize": int(maximum),
        "desiredSize": int(desired),
    },
}
temporary.write_text(
    json.dumps(record, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
os.replace(temporary, path)
PY
  apply_scaling 0 "$maximum" "$target"
  printf '%s\n' \
    'Capacity requested. Wait for three Ready GPU nodes before deploying.'
else
  if [[ ! -f "$baseline" ]]; then
    printf '[fail] no saved baseline at %s\n' "$baseline" >&2
    printf '%s\n' \
      'Inspect the node group and restore it manually; do not guess.' >&2
    exit 1
  fi
  active_account="$(
    aws sts get-caller-identity --query Account --output text
  )"
  read -r saved_minimum saved_maximum saved_desired < <(
    python3 - \
      "$baseline" \
      "$active_account" \
      "$AWS_REGION" \
      "$EKS_CLUSTER" \
      "$GPU_NODEGROUP" <<'PY'
import json
import sys

(
    path,
    expected_account,
    expected_region,
    expected_cluster,
    expected_nodegroup,
) = sys.argv[1:]
with open(path, encoding="utf-8") as handle:
    record = json.load(handle)
expected = {
    "account_id": expected_account,
    "region": expected_region,
    "cluster": expected_cluster,
    "nodegroup": expected_nodegroup,
}
for key, value in expected.items():
    if str(record.get(key)) != value:
        raise SystemExit(
            f"[fail] saved baseline has a different {key}: "
            f"{record.get(key)!r}"
        )
scaling = record["scaling"]
print(scaling["minSize"], scaling["maxSize"], scaling["desiredSize"])
PY
  )
  if [[ "$saved_minimum" != "0" || "$saved_desired" != "0" ]]; then
    printf '[fail] saved baseline was not an idle lab state\n' >&2
    exit 1
  fi
  apply_scaling "$saved_minimum" "$saved_maximum" "$saved_desired"
  printf '[ok] restored saved scaling min=%s max=%s desired=%s\n' \
    "$saved_minimum" "$saved_maximum" "$saved_desired"
  restored="${baseline%.json}-restored-$(date -u +%Y%m%dT%H%M%SZ)-$$.json"
  mv -- "$baseline" "$restored"
  printf '[ok] archived consumed baseline as %s\n' "$restored"
fi
