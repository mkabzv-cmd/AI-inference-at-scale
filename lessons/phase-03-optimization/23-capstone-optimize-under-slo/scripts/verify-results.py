#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


data = json.loads(
    Path(sys.argv[1] if len(sys.argv) > 1 else "artifacts/results.json")
    .read_text(encoding="utf-8")
)
if data["schema_version"] != "oms-capstone-selection/v1":
    raise SystemExit("unexpected schema")
if data["result_kind"] != "synthetic_selection_fixture_not_engine_measurement":
    raise SystemExit("fixture is not labelled synthetic")
by_id = {item["id"]: item for item in data["evaluated_candidates"]}
if by_id["b0-eager-small"]["feasible"]:
    raise SystemExit("baseline should fail the TTFT fixture gate")
if by_id["c2-prefix-cache"]["feasible"]:
    raise SystemExit("high-throughput candidate should fail success-rate gate")
if data["winner"] != "c1-graphs-capacity":
    raise SystemExit("wrong gated winner")
print("verified hard gates precede objective selection")
