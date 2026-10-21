#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


data = json.loads(
    Path(sys.argv[1] if len(sys.argv) > 1 else "artifacts/results.json")
    .read_text(encoding="utf-8")
)
assert data["schema_version"] == "oms-scheduler-simulation/v1"
assert data["result_kind"] == "discrete_event_simulation_not_engine_measurement"
experiments = {item["name"]: item for item in data["experiments"]}
static = experiments["static-baseline"]
continuous = experiments["continuous-controlled"]


def request(experiment: dict, request_id: str) -> dict:
    return next(item for item in experiment["requests"] if item["id"] == request_id)


if request(continuous, "short-late")["ttft_ticks"] >= request(
    static, "short-late"
)["ttft_ticks"]:
    raise SystemExit(
        "verification failed: continuous admission should improve late short TTFT"
    )
for experiment in experiments.values():
    if experiment["timeline"][-1]["used_blocks_after_free"] != 0:
        raise SystemExit("verification failed: allocator leaked pages")
    if any(
        item["peak_internal_fragmentation_tokens"] < 0
        for item in experiment["requests"]
    ):
        raise SystemExit("verification failed: impossible negative fragmentation")
print("verified admission effect, page accounting, and allocator cleanup")
