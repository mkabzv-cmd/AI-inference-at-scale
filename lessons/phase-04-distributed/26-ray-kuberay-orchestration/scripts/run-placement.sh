#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:?set LAB_NAMESPACE}"
mkdir -p artifacts
head_pod="$(
  kubectl -n "$LAB_NAMESPACE" get pod \
    -l ray.io/cluster=teaching-ray,ray.io/node-type=head \
    -o jsonpath='{.items[0].metadata.name}'
)"
[[ -n "$head_pod" ]] || {
  printf 'Ray head Pod not found\n' >&2
  exit 1
}

kubectl -n "$LAB_NAMESPACE" exec "$head_pod" -- \
  python /lesson/gpu_placement.py \
    --bundles 3 \
    --timeout-seconds 120 \
  | tee artifacts/placement-driver.log

python3 - artifacts/placement-driver.log artifacts/placement.json <<'PY'
import json
import sys
from pathlib import Path

source, output = map(Path, sys.argv[1:])
matches = [
    line.removeprefix("PLACEMENT_RESULT=")
    for line in source.read_text(encoding="utf-8").splitlines()
    if line.startswith("PLACEMENT_RESULT=")
]
if len(matches) != 1:
    raise SystemExit(f"expected one placement result, found {len(matches)}")
document = json.loads(matches[0])
output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
if not document["correctness"]["passed"]:
    raise SystemExit("placement correctness failed")
print(f"wrote {output}")
PY
