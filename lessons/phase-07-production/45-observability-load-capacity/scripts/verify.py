#!/usr/bin/env python3
"""Verify load evidence, correlation IDs, and a real SLO boundary."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def read_ndjson(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    records = read_ndjson(args.records)
    server_logs = read_ndjson(args.server_log)
    report = json.loads(args.report.read_text(encoding="utf-8"))
    failures = []
    request_ids = [str(item["request_id"]) for item in records]
    trace_ids = [str(item["trace_id"]) for item in records]
    logged = {
        str(item["request_id"]): str(item["trace_id"])
        for item in server_logs
    }

    if len(records) != 42:
        failures.append(f"expected 42 requests, found {len(records)}")
    if len(server_logs) != len(records):
        failures.append(
            f"expected one server completion per client record, found {len(server_logs)}"
        )
    if len(set(request_ids)) != len(request_ids):
        failures.append("request IDs are not unique")
    if len(logged) != len(server_logs):
        failures.append("server request IDs are not unique")
    if any(re.fullmatch(r"[0-9a-f]{32}", value) is None for value in trace_ids):
        failures.append("trace IDs are not 32 hex characters")
    if set(request_ids) != set(logged):
        failures.append("client and server request IDs do not correlate exactly")
    if any(item.get("server_request_id") != item["request_id"] for item in records):
        failures.append("response request IDs do not echo the client request IDs")
    if any(item.get("server_trace_id") != item["trace_id"] for item in records):
        failures.append("response trace IDs do not echo the client trace IDs")
    if any(logged.get(str(item["request_id"])) != item["trace_id"] for item in records):
        failures.append("client and server trace IDs do not correlate exactly")
    if any(item["status"] != 200 for item in records):
        failures.append("the bounded local fixture should have no HTTP errors")
    if len(report["stages"]) != 4:
        failures.append("capacity report must contain four stages")
    if not report["stages"][0]["slo_pass"]:
        failures.append("the concurrency-one baseline should pass the SLO")
    if report["first_slo_breach"] is None:
        failures.append("high concurrency did not expose an SLO boundary")
    if report["stages"][-1]["p95_queue_seconds"] <= 0.1:
        failures.append("high-concurrency queue evidence is unexpectedly small")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(
        "PASS: 42 requests correlate across client/server evidence; the "
        "baseline passes and higher concurrency exposes queue/TTFT saturation"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
