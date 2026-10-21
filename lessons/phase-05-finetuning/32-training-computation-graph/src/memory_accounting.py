#!/usr/bin/env python3
"""Calculate explicit inference and training memory components.

The inputs intentionally provide retained activation and workspace sizes rather
than pretending those values can be inferred exactly from parameter count.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


GIB = 1024**3


def component(
    name: str,
    elements: int,
    bytes_per_element: int,
) -> dict[str, int | float | str]:
    total_bytes = elements * bytes_per_element
    return {
        "name": name,
        "elements": elements,
        "bytes_per_element": bytes_per_element,
        "bytes": total_bytes,
        "gib": total_bytes / GIB,
    }


def calculate(case: dict[str, object]) -> dict[str, object]:
    parameter_count = int(case["parameter_count"])
    components = [
        component(
            "weights",
            parameter_count,
            int(case["weight_bytes_per_parameter"]),
        ),
        component(
            "gradients",
            parameter_count,
            int(case["gradient_bytes_per_parameter"]),
        ),
        component(
            "optimizer_state",
            parameter_count,
            int(case["optimizer_state_bytes_per_parameter"]),
        ),
        component(
            "master_weights",
            parameter_count,
            int(case["master_weight_bytes_per_parameter"]),
        ),
        component(
            "retained_activations",
            int(case["retained_activation_elements"]),
            int(case["activation_bytes_per_element"]),
        ),
        {
            "name": "kv_cache",
            "elements": None,
            "bytes_per_element": None,
            "bytes": int(case["kv_cache_bytes"]),
            "gib": int(case["kv_cache_bytes"]) / GIB,
        },
        {
            "name": "workspace",
            "elements": None,
            "bytes_per_element": None,
            "bytes": int(case["workspace_bytes"]),
            "gib": int(case["workspace_bytes"]) / GIB,
        },
    ]
    total_bytes = sum(int(item["bytes"]) for item in components)
    return {
        "name": str(case["name"]),
        "mode": str(case["mode"]),
        "components": components,
        "total_bytes": total_bytes,
        "total_gib": total_bytes / GIB,
        "warning": (
            "This is a planning model, not an allocator guarantee. Framework "
            "caches, fragmentation, temporary kernels, and implementation "
            "choices require measured headroom."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    document = json.loads(args.cases.read_text(encoding="utf-8"))
    results = [calculate(case) for case in document["cases"]]
    payload = {
        "schema_version": 1,
        "source": str(args.cases),
        "cases": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for result in results:
        print(f"{result['name']}: {result['total_gib']:.2f} GiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
