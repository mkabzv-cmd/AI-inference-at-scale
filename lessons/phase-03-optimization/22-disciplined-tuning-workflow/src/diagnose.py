#!/usr/bin/env python3
"""Turn symptoms into falsifiable bottleneck hypotheses."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def diagnose(case: dict[str, Any]) -> dict[str, Any]:
    symptoms = case["symptoms"]
    observations = case["controlled_observations"]
    if (
        symptoms["kv_cache_utilization_percent"] >= 95
        and observations.get("preemption_count", 0) > 0
    ):
        primary = "kv_capacity_and_preemption"
        evidence = [
            "KV utilization >=95%",
            "preemption_count > 0",
            "recomputed_tokens > 0",
        ]
        test = (
            "Hold workload constant; raise available KV budget slightly or "
            "lower max concurrency/context, then check preemption and p95."
        )
    elif (
        observations.get("arrival_rate_rps", 0)
        > observations.get("completion_rate_rps", float("inf"))
        and symptoms["request_queue_p95_ms"] > symptoms["tpot_p95_ms"] * 10
    ):
        primary = "admission_queue_saturation"
        evidence = [
            "arrival rate exceeds completion rate",
            "queue p95 dominates token time",
            "GPU utilization is already high",
        ]
        test = (
            "Hold request distribution fixed; reduce offered load to measured "
            "capacity or change one scheduler limit and observe queue slope."
        )
    elif (
        symptoms["gpu_utilization_percent"] < 30
        and symptoms["request_queue_p95_ms"] < 10
        and observations.get("client_think_time_mean_ms", 0) > 0
    ):
        primary = "client_pacing_or_backpressure"
        evidence = [
            "low GPU utilization",
            "nearly empty server queue",
            "client e2e exceeds server e2e",
            "closed-loop think time is present",
        ]
        test = (
            "Use a calibrated open-loop generator at a safe rate while holding "
            "server/model constant; compare server and client timestamps."
        )
    else:
        primary = "undetermined"
        evidence = ["fixture does not satisfy one high-confidence rule"]
        test = "Collect a timeline and one layer-specific metric before tuning."
    return {
        "case_id": case["case_id"],
        "result_kind": case["result_kind"],
        "primary_hypothesis": primary,
        "supporting_evidence": evidence,
        "falsification_test": test,
        "expected_fixture_answer": case["expected_primary_bottleneck"],
        "matched_fixture_answer": primary
        == case["expected_primary_bottleneck"],
    }


def compare(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    gate: dict[str, Any],
) -> dict[str, Any]:
    reasons = []
    base = baseline["summary"]
    cand = candidate["summary"]
    if (
        gate["require_same_workload_hash"]
        and baseline["controlled_workload_hash"]
        != candidate["controlled_workload_hash"]
    ):
        reasons.append("workload hash changed")
    if (
        gate["require_same_output_tokens_mean"]
        and base["output_tokens_mean"] != cand["output_tokens_mean"]
    ):
        reasons.append("mean output length changed")
    if cand["success_rate"] < gate["minimum_success_rate"]:
        reasons.append("success-rate gate failed")
    if cand["quality_pass_rate"] < gate["minimum_quality_pass_rate"]:
        reasons.append("quality gate failed")
    if cand["ttft_p95_ms"] > gate["maximum_ttft_p95_ms"]:
        reasons.append("TTFT SLO failed")
    if cand["tpot_p95_ms"] > gate["maximum_tpot_p95_ms"]:
        reasons.append("TPOT SLO failed")
    return {
        "baseline_run_id": baseline["run_id"],
        "candidate_run_id": candidate["run_id"],
        "candidate_reported_throughput_gain_percent": (
            (cand["request_throughput_rps"] / base["request_throughput_rps"] - 1)
            * 100
        ),
        "accepted": not reasons,
        "rejection_reasons": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, action="append", required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {
        "schema_version": "oms-tuning-workflow/v1",
        "result_kind": "synthetic_case_analysis_not_engine_measurement",
        "diagnoses": [diagnose(load(path)) for path in args.case],
        "comparison": compare(
            load(args.baseline), load(args.candidate), load(args.gate)
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for item in result["diagnoses"]:
        print(f"{item['case_id']:<14} -> {item['primary_hypothesis']}")
    print(
        "candidate accepted:",
        result["comparison"]["accepted"],
        "; reasons:",
        ", ".join(result["comparison"]["rejection_reasons"]),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
