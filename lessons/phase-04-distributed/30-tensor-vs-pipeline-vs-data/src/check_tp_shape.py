#!/usr/bin/env python3
"""Conservative TP divisibility preflight for a model config."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--tp", type=int, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.tp < 1:
        raise SystemExit("TP must be positive")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    checks = {
        "hidden_size": int(config["hidden_size"]),
        "attention_heads": int(config["num_attention_heads"]),
        "kv_heads": int(
            config.get(
                "num_key_value_heads", config["num_attention_heads"]
            )
        ),
    }
    failures = [
        f"{name}={value} is not divisible by TP={args.tp}"
        for name, value in checks.items()
        if value % args.tp
    ]
    document = {
        "tp": args.tp,
        "checks": checks,
        "valid": not failures,
        "failures": failures,
        "warning": (
            "Conservative arithmetic only; confirm exact engine architecture "
            "and KV-head replication support."
        ),
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(document, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
