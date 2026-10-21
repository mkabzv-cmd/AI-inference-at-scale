#!/usr/bin/env python3
"""Verify the local lesson-24 result contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} SUMMARY_JSON")
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["strategy"] == "collective"
    assert data["correctness"]["passed"] is True
    assert data["environment"]["world_size"] == 3
    assert {item["rank"] for item in data["ranks"]} == {0, 1, 2}
    assert {item["backend"] for item in data["ranks"]} == {"gloo"}
    print("lesson-24 local distributed contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
