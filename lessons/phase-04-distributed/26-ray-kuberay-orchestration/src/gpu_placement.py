#!/usr/bin/env python3
"""Reserve GPU bundles and prove actor placement across Ray nodes."""

from __future__ import annotations

import argparse
import json
import os
import socket

import ray
from ray.util.placement_group import placement_group, remove_placement_group
from ray.util.scheduling_strategies import PlacementGroupSchedulingStrategy


@ray.remote(num_cpus=0.25, num_gpus=1)
class GpuWitness:
    def inspect(self) -> dict[str, object]:
        context = ray.get_runtime_context()
        try:
            import torch

            cuda_available = torch.cuda.is_available()
            device_name = (
                torch.cuda.get_device_name(0) if cuda_available else None
            )
        except ImportError:
            cuda_available = None
            device_name = None
        return {
            "hostname": socket.gethostname(),
            "ray_node_id": str(context.get_node_id()),
            "ray_worker_id": str(context.get_worker_id()),
            "ray_gpu_ids": ray.get_gpu_ids(),
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "cuda_available": cuda_available,
            "cuda_device_name": device_name,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundles", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=float, default=60)
    parser.add_argument("--expect-infeasible", action="store_true")
    args = parser.parse_args()
    if args.bundles < 1:
        raise SystemExit("bundles must be positive")

    ray.init(address="auto")
    group = placement_group(
        [{"GPU": 1, "CPU": 0.25} for _ in range(args.bundles)],
        strategy="STRICT_SPREAD",
        name=f"lesson-26-{args.bundles}-gpu-bundles",
    )
    ready = True
    error = None
    try:
        ray.get(group.ready(), timeout=args.timeout_seconds)
    except ray.exceptions.GetTimeoutError as exc:
        ready = False
        error = type(exc).__name__

    actors = []
    if ready:
        handles = [
            GpuWitness.options(
                scheduling_strategy=PlacementGroupSchedulingStrategy(
                    placement_group=group,
                    placement_group_bundle_index=index,
                    placement_group_capture_child_tasks=True,
                )
            ).remote()
            for index in range(args.bundles)
        ]
        actors = ray.get([actor.inspect.remote() for actor in handles])

    expected = not ready if args.expect_infeasible else ready
    unique_hosts = len({item["hostname"] for item in actors})
    unique_nodes = len({item["ray_node_id"] for item in actors})
    placement_valid = (
        args.expect_infeasible
        or (
            len(actors) == args.bundles
            and unique_hosts == args.bundles
            and unique_nodes == args.bundles
            and all(len(item["ray_gpu_ids"]) == 1 for item in actors)
        )
    )
    document = {
        "schema_version": 1,
        "experiment_id": f"lesson-26-bundles-{args.bundles}",
        "strategy": "ray-placement",
        "correctness": {"passed": expected and placement_valid},
        "environment": {
            "ray_version": ray.__version__,
            "cluster_resources": ray.cluster_resources(),
            "available_resources": ray.available_resources(),
            "distinct_hosts": unique_hosts,
            "distinct_ray_nodes": unique_nodes,
        },
        "measurements": {
            "requested_bundles": args.bundles,
            "placement_group_ready": ready,
            "actor_count": len(actors),
            "timeout_seconds": args.timeout_seconds,
        },
        "actors": actors,
        "failure": {"type": error},
        "limitations": [
            "Ray logical resource evidence must be joined with Kubernetes placement"
        ],
    }
    print("PLACEMENT_RESULT=" + json.dumps(document, sort_keys=True))
    remove_placement_group(group)
    ray.shutdown()
    return 0 if document["correctness"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
