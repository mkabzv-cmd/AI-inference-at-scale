#!/usr/bin/env bash
set -euo pipefail

: "${LAB_NAMESPACE:?set LAB_NAMESPACE}"
mkdir -p artifacts
head_pod="$(
  kubectl -n "$LAB_NAMESPACE" get pod \
    -l ray.io/cluster=teaching-ray,ray.io/node-type=head \
    -o jsonpath='{.items[0].metadata.name}'
)"
kubectl -n "$LAB_NAMESPACE" exec "$head_pod" -- \
  python /lesson/gpu_placement.py \
    --bundles 4 \
    --timeout-seconds 15 \
    --expect-infeasible \
  | tee artifacts/impossible-driver.log

python3 - artifacts/impossible-driver.log \
  artifacts/impossible-placement.json <<'PY'
import json
import sys
from pathlib import Path

source, output = map(Path, sys.argv[1:])
records = [
    json.loads(line.removeprefix("PLACEMENT_RESULT="))
    for line in source.read_text(encoding="utf-8").splitlines()
    if line.startswith("PLACEMENT_RESULT=")
]
if len(records) != 1 or not records[0]["correctness"]["passed"]:
    raise SystemExit("expected one passing infeasible-placement record")
output.write_text(json.dumps(records[0], indent=2, sort_keys=True) + "\n")
print(f"wrote {output}")
PY
