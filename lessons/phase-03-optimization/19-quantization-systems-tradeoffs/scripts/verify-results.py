#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


results_path = Path(
    sys.argv[1] if len(sys.argv) > 1 else "artifacts/results.json"
)
gate_path = Path(
    sys.argv[2] if len(sys.argv) > 2 else "configs/quality-gate.json"
)
data = json.loads(results_path.read_text(encoding="utf-8"))
gate = json.loads(gate_path.read_text(encoding="utf-8"))
if data["schema_version"] != "oms-toy-quantization/v1":
    raise SystemExit("unexpected result schema")
items = {item["name"]: item for item in data["experiments"]}
g32 = items["int4-group-32"]
g8 = items["int4-group-8"]
if (
    g8["numeric_error"]["mean_relative_l2_output_error"]
    >= g32["numeric_error"]["mean_relative_l2_output_error"]
):
    raise SystemExit("smaller groups should reduce error in this fixed fixture")
passing = [
    item["name"]
    for item in data["experiments"]
    if item["compression_ratio_vs_fp16"] >= gate["minimum_compression_ratio"]
    and item["numeric_error"][gate["metric"]] <= gate["maximum"]
]
if not passing:
    raise SystemExit("no quantized candidate passed the toy gate")
print("toy gate passed by:", ", ".join(passing))
print("warning: passing this gate says nothing about LLM task quality or kernels")
