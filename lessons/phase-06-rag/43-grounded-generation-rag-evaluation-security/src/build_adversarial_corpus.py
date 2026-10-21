#!/usr/bin/env python3
"""Create a generated corpus snapshot containing an untrusted injection fixture."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--additional", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = args.base.read_text(encoding="utf-8").rstrip("\n")
    additional = args.additional.read_text(encoding="utf-8").strip()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(base + "\n" + additional + "\n", encoding="utf-8")
    print(f"wrote adversarial corpus snapshot to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
