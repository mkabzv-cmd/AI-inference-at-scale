#!/usr/bin/env python3
"""Convert failure-drill NDJSON events into a readable timeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    events = [
        json.loads(line)
        for line in args.input.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not events or any("timestamp" not in event for event in events):
        raise SystemExit("timeline needs timestamped events")
    lines = [
        "# Failure and recovery timeline",
        "",
        "| timestamp | event | detail |",
        "|---|---|---|",
    ]
    for event in events:
        detail = json.dumps(
            {
                key: value
                for key, value in event.items()
                if key not in {"timestamp", "event"}
            },
            sort_keys=True,
        ).replace("|", "\\|")
        lines.append(
            f"| {event['timestamp']} | {event.get('event', '')} | {detail} |"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.output}; events={len(events)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
