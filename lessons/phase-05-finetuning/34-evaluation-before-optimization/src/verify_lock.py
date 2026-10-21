#!/usr/bin/env python3
"""Verify that the frozen acceptance set and evaluation config are unchanged."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--acceptance", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--evaluator", type=Path, required=True)
    args = parser.parse_args()

    lock = json.loads(args.lock.read_text(encoding="utf-8"))
    observed = {
        "acceptance_sha256": sha256_file(args.acceptance),
        "evaluation_config_sha256": sha256_file(args.config),
        "evaluator_sha256": sha256_file(args.evaluator),
    }
    failures = [
        key
        for key, value in observed.items()
        if value != lock.get(key)
    ]
    if failures:
        for key in failures:
            print(f"FAIL: {key} differs from frozen contract")
        return 1
    print("PASS: acceptance set and evaluation configuration match the lock")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
