#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


data = json.loads(
    Path(sys.argv[1] if len(sys.argv) > 1 else "artifacts/results.json")
    .read_text(encoding="utf-8")
)
for experiment in data["experiments"]:
    print(f"\n## {experiment['name']}")
    print("tick | scheduled | waiting | active | used/free pages")
    print("---: | --- | --- | --- | ---:")
    for event in experiment["timeline"]:
        scheduled = ", ".join(
            f"{item['id']}:{item['phase']}+{item['tokens']}"
            for item in event["scheduled"]
        ) or "-"
        waiting = ", ".join(event["waiting"]) or "-"
        active = ", ".join(event["active"]) or "-"
        print(
            f"{event['tick']} | {scheduled} | {waiting} | {active} | "
            f"{event['used_blocks_after_free']}/"
            f"{event['free_blocks_after_free']}"
        )
