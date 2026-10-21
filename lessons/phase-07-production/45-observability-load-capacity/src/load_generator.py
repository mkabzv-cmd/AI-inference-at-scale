#!/usr/bin/env python3
"""Run staged concurrent load and retain one JSON record per request."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


def one_request(
    base_url: str,
    path: str,
    timeout: float,
    prompt: str,
    max_tokens: int,
    stage: str,
    ordinal: int,
) -> dict[str, object]:
    request_id = f"{stage}-{ordinal:04d}-{uuid.uuid4().hex[:8]}"
    trace_id = uuid.uuid4().hex
    span_id = uuid.uuid4().hex[:16]
    traceparent = f"00-{trace_id}-{span_id}-01"
    body = json.dumps(
        {
            "model": "oms-capacity-simulator",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": max_tokens,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Request-ID": request_id,
            "traceparent": traceparent,
        },
        method="POST",
    )
    started_wall = time.time()
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = json.loads(response.read().decode("utf-8"))
            headers = response.headers
            status = response.status
        error = None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        response_body = None
        headers = {}
        status = 0
        error = f"{type(exc).__name__}: {exc}"
    observed_total = time.perf_counter() - started
    return {
        "schema_version": 1,
        "stage": stage,
        "ordinal": ordinal,
        "request_id": request_id,
        "trace_id": trace_id,
        "server_request_id": headers.get("X-Request-ID"),
        "server_trace_id": headers.get("X-Trace-ID"),
        "started_unix_seconds": started_wall,
        "status": status,
        "error": error,
        "client_total_seconds": observed_total,
        "server_queue_seconds": float(headers.get("X-Queue-Seconds", "nan")),
        "server_ttft_seconds": float(headers.get("X-TTFT-Seconds", "nan")),
        "server_itl_seconds": float(headers.get("X-ITL-Seconds", "nan")),
        "server_total_seconds": float(headers.get("X-Total-Seconds", "nan")),
        "prompt_tokens": (
            response_body.get("usage", {}).get("prompt_tokens")
            if response_body
            else None
        ),
        "completion_tokens": (
            response_body.get("usage", {}).get("completion_tokens")
            if response_body
            else None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    records = []
    stage_windows = {}
    for stage in plan["stages"]:
        name = str(stage["name"])
        concurrency = int(stage["concurrency"])
        requests = int(stage["requests"])
        print(f"stage={name} concurrency={concurrency} requests={requests}")
        started = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=concurrency
        ) as executor:
            futures = [
                executor.submit(
                    one_request,
                    args.base_url,
                    str(plan["endpoint_path"]),
                    float(plan["request_timeout_seconds"]),
                    str(plan["prompt"]),
                    int(plan["max_tokens"]),
                    name,
                    ordinal,
                )
                for ordinal in range(requests)
            ]
            for future in concurrent.futures.as_completed(futures):
                records.append(future.result())
        stage_windows[name] = time.perf_counter() - started

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    metadata = {
        "schema_version": 1,
        "base_url": args.base_url,
        "plan": str(args.plan),
        "stage_elapsed_seconds": stage_windows,
        "records": len(records),
    }
    args.output.with_suffix(".metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote={len(records)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
