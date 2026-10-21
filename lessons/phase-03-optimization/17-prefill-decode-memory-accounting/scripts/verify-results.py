#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit("verification failed: " + message)


path = Path(sys.argv[1] if len(sys.argv) > 1 else "artifacts/results.json")
data = json.loads(path.read_text(encoding="utf-8"))
if data.get("schema_version") != "oms-optimization-memory/v1":
    fail("unexpected schema_version")
if data.get("result_kind") != "analytical_prediction_not_measurement":
    fail("analytical results are not labelled as predictions")
scenarios = data.get("scenarios", [])
if len(scenarios) != 4:
    fail("expected four scenarios")
by_name = {item["name"]: item for item in scenarios}
short = by_name["interactive-short"]
long = by_name["interactive-long"]
concurrent = by_name["concurrent-medium"]
oom = by_name["safe-simulated-oom"]
if long["kv"]["allocated_gib"] <= short["kv"]["allocated_gib"]:
    fail("long context should allocate more KV memory")
if concurrent["kv"]["allocated_gib"] <= long["kv"]["allocated_gib"]:
    fail("concurrency should increase KV memory")
if oom["predicted_fit"]:
    fail("safe simulated OOM scenario unexpectedly fits")
if not short["predicted_fit"]:
    fail("small baseline unexpectedly does not fit")
print("verified memory monotonicity, labels, baseline fit, and safe OOM boundary")
