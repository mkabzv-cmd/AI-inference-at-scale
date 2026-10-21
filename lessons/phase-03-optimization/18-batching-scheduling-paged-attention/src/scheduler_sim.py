#!/usr/bin/env python3
"""Small discrete-event model of static/continuous LLM scheduling.

Ticks and work units are intentionally abstract. The simulation is useful for
reasoning about admission, head-of-line blocking, token budgets, and KV pages;
it is not a latency predictor.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def pages(tokens: int, block_size: int) -> int:
    return math.ceil(tokens / block_size) if tokens else 0


def simulate(
    request_specs: list[dict[str, Any]],
    policy: str,
    max_num_seqs: int,
    token_budget: int,
    block_size: int,
    total_blocks: int,
) -> dict[str, Any]:
    requests = []
    for spec in copy.deepcopy(request_specs):
        requests.append(
            {
                **spec,
                "state": "waiting",
                "prefill_remaining": int(spec["prompt_tokens"]),
                "decode_remaining": int(spec["output_tokens"]),
                "cached_tokens": 0,
                "allocated_blocks": 0,
                "first_scheduled_tick": None,
                "first_token_tick": None,
                "finish_tick": None,
                "peak_blocks": 0,
            }
        )

    active: list[dict[str, Any]] = []
    timeline = []
    tick = 0
    max_ticks = 10000

    while any(request["state"] != "finished" for request in requests):
        if tick >= max_ticks:
            raise RuntimeError("simulation did not converge")
        arrived = [
            request
            for request in requests
            if request["state"] == "waiting"
            and request["arrival_tick"] <= tick
        ]
        can_admit = policy == "continuous" or not active
        if can_admit:
            for request in arrived:
                if len(active) >= max_num_seqs:
                    break
                request["state"] = "active"
                request["first_scheduled_tick"] = tick
                active.append(request)

        budget = token_budget
        scheduled = []
        # Oldest arrival first makes the fairness policy explicit.
        for request in sorted(
            active, key=lambda item: (item["arrival_tick"], item["id"])
        ):
            if budget <= 0:
                break
            if request["prefill_remaining"] > 0:
                tokens = min(request["prefill_remaining"], budget)
                proposed_cached = request["cached_tokens"] + tokens
                proposed_blocks = pages(proposed_cached, block_size)
                extra_blocks = proposed_blocks - request["allocated_blocks"]
                used_blocks = sum(item["allocated_blocks"] for item in active)
                if used_blocks + extra_blocks > total_blocks:
                    continue
                request["prefill_remaining"] -= tokens
                request["cached_tokens"] = proposed_cached
                request["allocated_blocks"] = proposed_blocks
                request["peak_blocks"] = max(
                    request["peak_blocks"], proposed_blocks
                )
                budget -= tokens
                scheduled.append(
                    {
                        "id": request["id"],
                        "phase": "prefill",
                        "tokens": tokens,
                    }
                )
            elif request["decode_remaining"] > 0 and budget > 0:
                proposed_cached = request["cached_tokens"] + 1
                proposed_blocks = pages(proposed_cached, block_size)
                extra_blocks = proposed_blocks - request["allocated_blocks"]
                used_blocks = sum(item["allocated_blocks"] for item in active)
                if used_blocks + extra_blocks > total_blocks:
                    continue
                request["decode_remaining"] -= 1
                request["cached_tokens"] = proposed_cached
                request["allocated_blocks"] = proposed_blocks
                request["peak_blocks"] = max(
                    request["peak_blocks"], proposed_blocks
                )
                budget -= 1
                if request["first_token_tick"] is None:
                    request["first_token_tick"] = tick
                scheduled.append(
                    {"id": request["id"], "phase": "decode", "tokens": 1}
                )

        finished_now = []
        for request in list(active):
            if (
                request["prefill_remaining"] == 0
                and request["decode_remaining"] == 0
            ):
                request["state"] = "finished"
                request["finish_tick"] = tick + 1
                finished_now.append(request["id"])
                active.remove(request)
                request["allocated_blocks"] = 0

        used_blocks = sum(item["allocated_blocks"] for item in active)
        timeline.append(
            {
                "tick": tick,
                "scheduled": scheduled,
                "finished": finished_now,
                "waiting": [
                    item["id"]
                    for item in requests
                    if item["state"] == "waiting"
                    and item["arrival_tick"] <= tick
                ],
                "active": [item["id"] for item in active],
                "used_blocks_after_free": used_blocks,
                "free_blocks_after_free": total_blocks - used_blocks,
            }
        )
        tick += 1

    request_results = []
    for request in requests:
        payload_tokens = request["prompt_tokens"] + request["output_tokens"]
        allocated_token_slots = request["peak_blocks"] * block_size
        request_results.append(
            {
                "id": request["id"],
                "arrival_tick": request["arrival_tick"],
                "first_scheduled_tick": request["first_scheduled_tick"],
                "first_token_tick": request["first_token_tick"],
                "finish_tick": request["finish_tick"],
                "queue_ticks": (
                    request["first_scheduled_tick"] - request["arrival_tick"]
                ),
                "ttft_ticks": (
                    request["first_token_tick"] - request["arrival_tick"]
                ),
                "e2e_ticks": request["finish_tick"] - request["arrival_tick"],
                "peak_blocks": request["peak_blocks"],
                "peak_internal_fragmentation_tokens": (
                    allocated_token_slots - payload_tokens
                ),
            }
        )

    return {
        "policy": policy,
        "configuration": {
            "max_num_seqs": max_num_seqs,
            "max_num_batched_tokens": token_budget,
            "block_size_tokens": block_size,
            "total_blocks": total_blocks,
        },
        "ticks_to_drain": tick,
        "requests": request_results,
        "timeline": timeline,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workload", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    workload = load(args.workload)
    matrix = load(args.matrix)
    controlled = matrix["controlled_variables"]
    experiments = []
    for item in matrix["experiments"]:
        experiments.append(
            {
                "name": item["name"],
                **simulate(
                    workload["requests"],
                    item["policy"],
                    int(item["max_num_seqs"]),
                    int(item["max_num_batched_tokens"]),
                    int(controlled["block_size_tokens"]),
                    int(controlled["total_blocks"]),
                ),
            }
        )
    result = {
        "schema_version": "oms-scheduler-simulation/v1",
        "result_kind": "discrete_event_simulation_not_engine_measurement",
        "workload": workload,
        "experiments": experiments,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for experiment in experiments:
        short = next(
            item
            for item in experiment["requests"]
            if item["id"] == "short-late"
        )
        print(
            f"{experiment['name']:<34} "
            f"drain={experiment['ticks_to_drain']:>3} ticks "
            f"short-late ttft={short['ttft_ticks']:>3} ticks"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
