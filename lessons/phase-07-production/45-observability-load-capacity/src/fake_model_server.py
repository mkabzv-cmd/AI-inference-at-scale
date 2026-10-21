#!/usr/bin/env python3
"""A bounded model-server simulator with queue, TTFT, ITL, logs, and metrics."""

from __future__ import annotations

import argparse
import json
import re
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class State:
    def __init__(self, capacity: int, log_path: Path) -> None:
        self.slots = threading.BoundedSemaphore(capacity)
        self.capacity = capacity
        self.log_path = log_path
        self.lock = threading.Lock()
        self.in_flight = 0
        self.queued = 0
        self.completed = 0
        self.errors = 0
        self.queue_seconds = 0.0

    def log(self, record: dict[str, object]) -> None:
        with self.lock:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")


STATE: State
TRACEPARENT = re.compile(
    r"^(?P<version>[0-9a-f]{2})-"
    r"(?P<trace>[0-9a-f]{32})-"
    r"(?P<span>[0-9a-f]{16})-"
    r"(?P<flags>[0-9a-f]{2})$"
)


class Handler(BaseHTTPRequestHandler):
    server_version = "oms-fake-model/1"

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def send_json(
        self,
        status: int,
        payload: dict[str, object],
        headers: dict[str, str] | None = None,
    ) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self.send_json(200, {"status": "ok"})
            return
        if self.path == "/readyz":
            self.send_json(200, {"status": "ready"})
            return
        if self.path == "/metrics":
            with STATE.lock:
                metrics = (
                    "# TYPE oms_requests_completed_total counter\n"
                    f"oms_requests_completed_total {STATE.completed}\n"
                    "# TYPE oms_requests_errors_total counter\n"
                    f"oms_requests_errors_total {STATE.errors}\n"
                    "# TYPE oms_requests_in_flight gauge\n"
                    f"oms_requests_in_flight {STATE.in_flight}\n"
                    "# TYPE oms_requests_queued gauge\n"
                    f"oms_requests_queued {STATE.queued}\n"
                    "# TYPE oms_queue_seconds_total counter\n"
                    f"oms_queue_seconds_total {STATE.queue_seconds:.6f}\n"
                    "# TYPE oms_model_capacity gauge\n"
                    f"oms_model_capacity {STATE.capacity}\n"
                ).encode("utf-8")
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/plain; version=0.0.4; charset=utf-8",
            )
            self.send_header("Content-Length", str(len(metrics)))
            self.end_headers()
            self.wfile.write(metrics)
            return
        self.send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self.send_json(404, {"error": "not found"})
            return

        started = time.perf_counter()
        request_id = self.headers.get("X-Request-ID") or str(uuid.uuid4())
        traceparent = self.headers.get("traceparent", "").lower()
        trace_match = TRACEPARENT.fullmatch(traceparent)
        trace_id_value = (
            trace_match.group("trace") if trace_match else uuid.uuid4().hex
        )
        try:
            length = int(self.headers.get("Content-Length", "0"))
            document = json.loads(self.rfile.read(length).decode("utf-8"))
            messages = document["messages"]
            prompt = " ".join(str(item["content"]) for item in messages)
            output_tokens = min(int(document.get("max_tokens", 16)), 32)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            with STATE.lock:
                STATE.errors += 1
            self.send_json(400, {"error": "invalid request"})
            return

        with STATE.lock:
            STATE.queued += 1
        wait_started = time.perf_counter()
        STATE.slots.acquire()
        queue_seconds = time.perf_counter() - wait_started
        with STATE.lock:
            STATE.queued -= 1
            STATE.in_flight += 1
            STATE.queue_seconds += queue_seconds

        try:
            # The fixed floor creates a stable service time. Prompt words add a
            # small prefill term; generated tokens add an inter-token term.
            prefill_seconds = 0.04 + min(len(prompt.split()), 100) * 0.0005
            inter_token_seconds = 0.006
            time.sleep(prefill_seconds)
            ttft_seconds = time.perf_counter() - started
            time.sleep(output_tokens * inter_token_seconds)
            total_seconds = time.perf_counter() - started
            body = {
                "id": request_id,
                "model": "oms-capacity-simulator",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": (
                                "Inspect readiness, selector matching, and "
                                "EndpointSlices before changing the workload."
                            ),
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": output_tokens,
                },
            }
            self.send_json(
                200,
                body,
                {
                    "X-Request-ID": request_id,
                    "X-Trace-ID": trace_id_value,
                    "X-Queue-Seconds": f"{queue_seconds:.6f}",
                    "X-TTFT-Seconds": f"{ttft_seconds:.6f}",
                    "X-ITL-Seconds": f"{inter_token_seconds:.6f}",
                    "X-Total-Seconds": f"{total_seconds:.6f}",
                },
            )
            with STATE.lock:
                STATE.completed += 1
            STATE.log(
                {
                    "event": "request_complete",
                    "request_id": request_id,
                    "trace_id": trace_id_value,
                    "queue_seconds": queue_seconds,
                    "ttft_seconds": ttft_seconds,
                    "itl_seconds": inter_token_seconds,
                    "total_seconds": total_seconds,
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": output_tokens,
                }
            )
        finally:
            with STATE.lock:
                STATE.in_flight -= 1
            STATE.slots.release()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8045)
    parser.add_argument("--capacity", type=int, default=2)
    parser.add_argument("--log-path", type=Path, required=True)
    args = parser.parse_args()
    if args.capacity < 1:
        parser.error("--capacity must be positive")
    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        parser.error("the teaching server may bind only to loopback")

    global STATE
    STATE = State(args.capacity, args.log_path)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(
        f"listening=http://{args.host}:{args.port} capacity={args.capacity}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
