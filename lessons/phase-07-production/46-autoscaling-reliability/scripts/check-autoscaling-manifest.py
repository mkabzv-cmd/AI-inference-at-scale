#!/usr/bin/env python3
"""Reject the lesson's deliberately inappropriate CPU-only HPA."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    text = args.manifest.read_text(encoding="utf-8")
    failures = []
    if "kind: HorizontalPodAutoscaler" not in text:
        failures.append("not an HPA manifest")
    if "name: cpu" in text and "oms_requests_queued" not in text:
        failures.append("CPU-only signal does not represent model queue demand")
    if "maxReplicas: 20" in text:
        failures.append("replica bound exceeds this lesson's cost ceiling")
    if "behavior:" not in text:
        failures.append("missing scale stabilization behavior")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: autoscaling manifest has bounded, stabilized demand scaling")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
