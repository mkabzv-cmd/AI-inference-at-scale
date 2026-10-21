#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shapes", type=Path, required=True)
    parser.add_argument("--trace", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    shapes = []
    for shape in load(args.shapes)["shapes"]:
        score_elements = (
            shape["batch"]
            * shape["heads"]
            * shape["query_tokens"]
            * shape["key_value_tokens"]
        )
        tiled_peak = (
            shape["batch"]
            * shape["heads"]
            * min(shape["tile_q"], shape["query_tokens"])
            * min(shape["tile_k"], shape["key_value_tokens"])
        )
        shapes.append(
            {
                **shape,
                "materialized_score_elements": score_elements,
                "materialized_score_bytes_fp16": score_elements * 2,
                "illustrative_tile_score_elements": tiled_peak,
                "query_tiles": math.ceil(
                    shape["query_tokens"] / shape["tile_q"]
                ),
                "key_tiles": math.ceil(
                    shape["key_value_tokens"] / shape["tile_k"]
                ),
                "warning": (
                    "tile occupancy and IO depend on the actual kernel; this "
                    "is shape arithmetic only"
                ),
            }
        )
    traces = []
    for path in args.trace:
        trace = load(path)
        traces.append(
            {
                "mode": trace["mode"],
                "visible_launch_count": len(trace["events"]),
                "visible_events": trace["events"],
                "captured_operations": trace.get("captured_operations", []),
                "result_kind": trace["result_kind"],
            }
        )
    result = {
        "schema_version": "oms-kernel-mechanisms/v1",
        "result_kind": "analytical_and_reference_cpu_not_gpu_profile",
        "shapes": shapes,
        "launch_structures": traces,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for shape in shapes:
        print(
            f"{shape['name']:<22} score elements="
            f"{shape['materialized_score_elements']:,} "
            f"fp16 score bytes={shape['materialized_score_bytes_fp16']:,}"
        )
    for trace in traces:
        print(
            f"{trace['mode']:<22} visible launches="
            f"{trace['visible_launch_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
