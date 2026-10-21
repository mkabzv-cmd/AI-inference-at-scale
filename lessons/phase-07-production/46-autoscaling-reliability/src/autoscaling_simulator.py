#!/usr/bin/env python3
"""Discrete autoscaling simulation with queues, cold starts, and backpressure."""

from __future__ import annotations

import argparse
import json
import math
from collections import deque
from pathlib import Path


def percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    if not ordered:
        return 0
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def desired_for(
    strategy: str,
    config: dict[str, object],
    queue_depth: int,
    ready: int,
) -> int:
    minimum = int(config["minimum_pods"])
    maximum = int(config["maximum_pods"])
    if strategy == "static":
        return minimum
    if strategy == "cpu":
        utilization = float(config["simulated_cpu_utilization"])
        target = float(config["cpu_target_utilization"])
        if utilization <= target:
            return max(minimum, ready)
        return min(maximum, max(minimum, math.ceil(ready * utilization / target)))
    if strategy == "queue":
        target = int(config["queue_target_per_pod"])
        if target <= 0:
            raise ValueError("queue_target_per_pod must be positive")
        return min(maximum, max(minimum, math.ceil(queue_depth / target)))
    raise ValueError(f"unknown strategy: {strategy}")


def simulate(strategy: str, config: dict[str, object]) -> dict[str, object]:
    minimum = int(config["minimum_pods"])
    maximum = int(config["maximum_pods"])
    cold_start = int(config["cold_start_steps"])
    service_per_pod = int(config["service_requests_per_ready_pod_step"])
    maximum_queue = int(config["maximum_queue"])
    scale_up_cooldown = int(config["scale_up_cooldown_steps"])
    scale_down_delay = int(config["scale_down_delay_steps"])
    arrivals = list(config["arrivals_per_step"])

    ready = minimum
    pending: list[int] = []
    desired = minimum
    queue: deque[int] = deque()
    waits: list[int] = []
    rejected = 0
    completed = 0
    scale_actions = 0
    steps_since_scale_up = 10**9
    idle_steps = 0
    timeline = []

    if minimum < 1 or maximum < minimum:
        raise ValueError("minimum_pods must be positive and no greater than maximum_pods")
    if cold_start < 0:
        raise ValueError("cold_start_steps cannot be negative")
    if service_per_pod < 1:
        raise ValueError("service_requests_per_ready_pod_step must be positive")
    if maximum_queue < 1:
        raise ValueError("maximum_queue must be positive")
    if scale_up_cooldown < 0 or scale_down_delay < 0:
        raise ValueError("scale cooldown and delay cannot be negative")
    if not arrivals or any(int(value) < 0 for value in arrivals):
        raise ValueError("arrivals_per_step must contain nonnegative demand")

    for step, arrivals_this_step in enumerate(arrivals):
        # Advance model loads.
        pending = [remaining - 1 for remaining in pending]
        became_ready = sum(remaining < 0 for remaining in pending)
        pending = [remaining for remaining in pending if remaining >= 0]
        ready += became_ready

        for _ in range(int(arrivals_this_step)):
            if len(queue) >= maximum_queue:
                rejected += 1
            else:
                queue.append(step)

        service_capacity = ready * service_per_pod
        served_now = min(service_capacity, len(queue))
        for _ in range(served_now):
            arrival_step = queue.popleft()
            waits.append(step - arrival_step)
        completed += served_now

        proposed = desired_for(strategy, config, len(queue), max(ready, 1))
        active_or_loading = ready + len(pending)
        if proposed > active_or_loading and steps_since_scale_up >= scale_up_cooldown:
            add = proposed - active_or_loading
            if cold_start == 0:
                ready += add
            else:
                pending.extend([cold_start - 1] * add)
            desired = proposed
            scale_actions += 1
            steps_since_scale_up = 0
            idle_steps = 0
        elif proposed < ready:
            if len(queue) == 0:
                idle_steps += 1
            else:
                idle_steps = 0
            if idle_steps >= scale_down_delay:
                remove = min(ready - proposed, ready - minimum)
                if remove > 0:
                    ready -= remove
                    desired = ready + len(pending)
                    scale_actions += 1
                idle_steps = 0
        else:
            if len(queue) == 0:
                idle_steps += 1
            else:
                idle_steps = 0
        steps_since_scale_up += 1

        timeline.append(
            {
                "step": step,
                "arrivals": arrivals_this_step,
                "ready_pods": ready,
                "loading_pods": len(pending),
                "desired_pods": desired,
                "queue_depth_after_service": len(queue),
                "served": served_now,
                "rejected_total": rejected,
            }
        )

    # Drain remaining work without accepting new traffic. This represents
    # backpressure plus a bounded observation tail, not infinite patience.
    drain_limit = 100
    drain_step = len(arrivals)
    while queue and drain_limit > 0:
        pending = [remaining - 1 for remaining in pending]
        became_ready = sum(remaining < 0 for remaining in pending)
        pending = [remaining for remaining in pending if remaining >= 0]
        ready += became_ready
        served_now = min(ready * service_per_pod, len(queue))
        for _ in range(served_now):
            waits.append(drain_step - queue.popleft())
        completed += served_now
        drain_step += 1
        drain_limit -= 1

    return {
        "strategy": strategy,
        "arrivals": sum(int(value) for value in arrivals),
        "completed": completed,
        "rejected": rejected,
        "left_queued": len(queue),
        "p50_wait_steps": percentile(waits, 0.50),
        "p95_wait_steps": percentile(waits, 0.95),
        "maximum_wait_steps": max(waits, default=0),
        "scale_actions": scale_actions,
        "peak_ready_pods": max(item["ready_pods"] for item in timeline),
        "peak_loading_pods": max(item["loading_pods"] for item in timeline),
        "timeline": timeline,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--strategies",
        nargs="+",
        choices=("static", "cpu", "queue"),
        default=("static", "cpu", "queue"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    results = [simulate(strategy, config) for strategy in args.strategies]
    payload = {
        "schema_version": 1,
        "step_seconds": config["step_seconds"],
        "configuration": config,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for result in results:
        print(
            f"{result['strategy']} rejected={result['rejected']} "
            f"p95_wait_steps={result['p95_wait_steps']} "
            f"scale_actions={result['scale_actions']} "
            f"peak_ready={result['peak_ready_pods']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
