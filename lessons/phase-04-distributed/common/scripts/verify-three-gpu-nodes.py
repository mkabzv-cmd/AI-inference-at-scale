#!/usr/bin/env python3
"""Verify that a selected EKS node group has three distinct one-GPU nodes."""

from __future__ import annotations

import argparse
import json
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodegroup", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    document = json.load(sys.stdin)
    selected = []
    for node in document.get("items", []):
        metadata = node.get("metadata", {})
        labels = metadata.get("labels", {})
        if labels.get("eks.amazonaws.com/nodegroup") != args.nodegroup:
            continue
        status = node.get("status", {})
        conditions = {
            item.get("type"): item.get("status")
            for item in status.get("conditions", [])
        }
        selected.append(
            {
                "name": metadata.get("name"),
                "ready": conditions.get("Ready"),
                "gpu": int(
                    status.get("allocatable", {}).get("nvidia.com/gpu", "0")
                ),
                "instance_type": labels.get(
                    "node.kubernetes.io/instance-type"
                ),
                "zone": labels.get("topology.kubernetes.io/zone"),
            }
        )

    print(json.dumps({"selected_nodes": selected}, indent=2, sort_keys=True))
    if len(selected) != 3:
        raise SystemExit(
            f"[fail] expected exactly 3 selected Nodes; found {len(selected)}"
        )
    if any(item["ready"] != "True" for item in selected):
        raise SystemExit("[fail] every selected Node must be Ready")
    if any(item["gpu"] != 1 for item in selected):
        raise SystemExit(
            "[fail] every selected Node must advertise exactly one GPU"
        )
    if len({item["name"] for item in selected}) != 3:
        raise SystemExit("[fail] selected node names are not unique")
    print("[ok] exactly three Ready one-GPU nodes selected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
