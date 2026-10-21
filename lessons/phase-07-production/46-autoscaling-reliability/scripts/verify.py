#!/usr/bin/env python3
"""Verify that queue scaling improves the authored demand scenario."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, required=True)
    args = parser.parse_args()
    study = json.loads(args.study.read_text(encoding="utf-8"))
    results = {item["strategy"]: item for item in study["results"]}
    slo = study["configuration"]["slo"]
    failures = []
    if set(results) != {"static", "cpu", "queue"}:
        failures.append("study must contain static, cpu, and queue strategies")
    else:
        static = results["static"]
        cpu = results["cpu"]
        queue = results["queue"]
        if cpu["peak_ready_pods"] != static["peak_ready_pods"]:
            failures.append("the low simulated CPU signal should not scale")
        if queue["peak_ready_pods"] <= static["peak_ready_pods"]:
            failures.append("queue signal did not add ready replicas")
        if queue["rejected"] >= static["rejected"]:
            failures.append("queue scaling did not reduce rejected requests")
        if queue["p95_wait_steps"] >= static["p95_wait_steps"]:
            failures.append("queue scaling did not reduce p95 waiting")
        if queue["scale_actions"] < 1:
            failures.append("queue strategy recorded no scaling action")
        queue_slo_pass = (
            queue["rejected"] <= slo["maximum_rejected_requests"]
            and queue["p95_wait_steps"] <= slo["maximum_p95_wait_steps"]
            and queue["scale_actions"] <= slo["maximum_scale_actions"]
        )
        static_slo_pass = (
            static["rejected"] <= slo["maximum_rejected_requests"]
            and static["p95_wait_steps"] <= slo["maximum_p95_wait_steps"]
            and static["scale_actions"] <= slo["maximum_scale_actions"]
        )
        if not queue_slo_pass:
            failures.append("queue strategy did not satisfy the authored SLO")
        if static_slo_pass:
            failures.append("static strategy unexpectedly satisfied the authored SLO")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(
        "PASS: the CPU signal misses demand while bounded queue scaling adds "
        "capacity and reduces rejection and waiting in the authored scenario"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
