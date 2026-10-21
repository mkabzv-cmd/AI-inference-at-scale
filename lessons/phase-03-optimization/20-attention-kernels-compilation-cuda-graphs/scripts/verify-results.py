#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


attention = json.loads(
    Path("artifacts/attention-correctness.json").read_text(encoding="utf-8")
)
results = json.loads(Path("artifacts/results.json").read_text(encoding="utf-8"))
if not attention["passed"]:
    raise SystemExit("online attention differs from materialized reference")
if results["result_kind"] != "analytical_and_reference_cpu_not_gpu_profile":
    raise SystemExit("non-measurements are not labelled")
traces = {
    item["mode"]: item["visible_launch_count"]
    for item in results["launch_structures"]
}
if not (
    traces["eager"] > traces["fused_attention"] > traces["cuda_graph_replay"]
):
    raise SystemExit("illustrative launch structure is inconsistent")
long_shape = next(
    item for item in results["shapes"] if item["name"] == "long-prefill"
)
short_shape = next(
    item for item in results["shapes"] if item["name"] == "short-prefill"
)
if long_shape["materialized_score_elements"] <= short_shape[
    "materialized_score_elements"
]:
    raise SystemExit("score matrix should grow with sequence length")
print("verified online-softmax correctness and mechanism-report invariants")
