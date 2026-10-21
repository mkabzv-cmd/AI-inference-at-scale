#!/usr/bin/env python3
"""Convert capstone benchmark files into the hard-gate selection input.

Peak GPU GiB is supplied explicitly because a single post-run nvidia-smi
snapshot is not a reliable peak. Use a reviewed time-series source.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument(
    "--candidate",
    action="append",
    required=True,
    metavar="ID=RESULTS_JSON=PEAK_GPU_GIB",
)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
candidates = []
for raw in args.candidate:
    try:
        candidate_id, path_text, peak_text = raw.split("=", 2)
        peak = float(peak_text)
    except ValueError as exc:
        raise SystemExit(f"invalid --candidate value: {raw}") from exc
    data = json.loads(Path(path_text).read_text(encoding="utf-8"))
    if data.get("schema_version") != "oms-benchmark/v1":
        raise SystemExit(f"{path_text}: expected oms-benchmark/v1")
    summary = data["summary"]
    required = (
        "success_rate",
        "quality_pass_rate",
        "ttft_p95_ms",
        "e2e_p95_ms",
        "output_throughput_tokens_per_second",
    )
    if any(summary.get(field) is None for field in required):
        raise SystemExit(f"{path_text}: missing required summary metric")
    candidates.append(
        {
            "id": candidate_id,
            **{field: summary[field] for field in required},
            "peak_gpu_memory_gib": peak,
            "source_results": path_text,
            "run_id": data.get("run_id"),
        }
    )
result = {
    "schema_version": "oms-capstone-result-set/v1",
    "result_kind": "measured_engine_results",
    "candidates": candidates,
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(f"assembled {len(candidates)} measured candidates")
