#!/usr/bin/env python3
"""Validate benchmark invariants without requiring a JSON Schema package."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("result", type=Path)
    parser.add_argument("--require-quality-rate", type=float, default=0.8)
    args = parser.parse_args()
    data = json.loads(args.result.read_text())
    assert data["schema_version"] == "oms-benchmark/v1"
    assert data["model"]["revision"] and len(data["model"]["revision"]) == 40
    workload = data["workload"]
    measured = [item for item in data["requests"] if not item["warmup"]]
    assert len(measured) == workload["measured_requests"]
    assert all(math.isfinite(item["e2e_ms"]) and item["e2e_ms"] >= 0 for item in measured)
    assert data["summary"]["success_rate"] == 1.0
    assert data["summary"]["quality_pass_rate"] >= args.require_quality_rate
    assert data["summary"]["latency_ms"]["p95"] is not None
    assert data["summary"]["ttft_ms"]["p50"] is not None
    print(
        f"valid {data['engine']['name']} run: "
        f"{len(measured)} requests, "
        f"quality={data['summary']['quality_pass_rate']:.1%}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
