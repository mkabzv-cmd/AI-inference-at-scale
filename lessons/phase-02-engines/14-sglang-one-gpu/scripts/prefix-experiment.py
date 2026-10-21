#!/usr/bin/env python3
"""Send alternating requests with a shared long prefix and record latency."""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.request
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--requests", type=int, default=12)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payloads = [
        json.loads(Path("requests/repeated-prefix-a.json").read_text()),
        json.loads(Path("requests/repeated-prefix-b.json").read_text()),
    ]
    records = []
    for index in range(args.requests):
        body = json.dumps(payloads[index % 2]).encode()
        request = urllib.request.Request(
            args.base_url + "/v1/chat/completions",
            data=body,
            headers={"content-type": "application/json"},
        )
        started = time.perf_counter()
        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.load(response)
        latency = (time.perf_counter() - started) * 1000
        records.append(
            {
                "index": index,
                "variant": "a" if index % 2 == 0 else "b",
                "latency_ms": round(latency, 3),
                "nonempty": bool(result["choices"][0]["message"]["content"].strip()),
            }
        )
    output = {
        "experiment": "shared-prefix-sequential",
        "requests": records,
        "latency_ms": {
            "first": records[0]["latency_ms"],
            "median_after_first": round(
                statistics.median(item["latency_ms"] for item in records[1:]), 3
            ),
        },
        "warning": "Client latency alone does not prove a cache hit; correlate server metrics/logs.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output["latency_ms"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
