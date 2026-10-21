#!/usr/bin/env python3
"""Enforce the configured scale-action budget."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, required=True)
    args = parser.parse_args()
    study = json.loads(args.study.read_text(encoding="utf-8"))
    budget = int(study["configuration"]["slo"]["maximum_scale_actions"])
    actions = int(study["results"][0]["scale_actions"])
    if actions > budget:
        print(
            f"FAIL: scale action budget exceeded: observed={actions} "
            f"allowed={budget}"
        )
        return 1
    print(f"PASS: scale actions {actions} are within budget {budget}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
