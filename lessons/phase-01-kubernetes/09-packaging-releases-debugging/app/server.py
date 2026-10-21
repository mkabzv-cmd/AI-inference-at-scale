#!/usr/bin/env python3
"""Tiny dependency-free HTTP service for learning Kubernetes releases."""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


STARTED_AT = time.monotonic()
MESSAGE = os.environ.get("APP_MESSAGE", "hello from lesson 09")
VERSION = os.environ.get("APP_VERSION", "dev")
FAULT_MODE = os.environ.get("FAULT_MODE", "none")
READY_DELAY_SECONDS = float(os.environ.get("READY_DELAY_SECONDS", "0"))
BIND_HOST = os.environ.get("BIND_HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8080"))


def is_ready() -> bool:
    if FAULT_MODE == "unready":
        return False
    return time.monotonic() - STARTED_AT >= READY_DELAY_SECONDS


class Handler(BaseHTTPRequestHandler):
    server_version = "lesson-service/1.0"

    def log_message(self, format_string: str, *args: object) -> None:
        print(
            json.dumps(
                {
                    "event": "http_access",
                    "client": self.client_address[0],
                    "message": format_string % args,
                },
                sort_keys=True,
            ),
            flush=True,
        )

    def send_json(self, status: HTTPStatus, body: dict[str, object]) -> None:
        payload = json.dumps(body, sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path == "/health/live":
            self.send_json(HTTPStatus.OK, {"live": True})
            return
        if self.path == "/health/ready":
            ready = is_ready()
            self.send_json(
                HTTPStatus.OK if ready else HTTPStatus.SERVICE_UNAVAILABLE,
                {"ready": ready, "fault_mode": FAULT_MODE},
            )
            return
        if self.path == "/version":
            self.send_json(HTTPStatus.OK, {"version": VERSION})
            return
        if self.path == "/":
            self.send_json(
                HTTPStatus.OK,
                {
                    "message": MESSAGE,
                    "version": VERSION,
                    "fault_mode": FAULT_MODE,
                },
            )
            return
        self.send_json(HTTPStatus.NOT_FOUND, {"detail": "not found"})


def main() -> int:
    if FAULT_MODE == "crash":
        print(
            json.dumps({"event": "deliberate_crash", "fault_mode": FAULT_MODE}),
            flush=True,
        )
        return 42

    if BIND_HOST not in {"127.0.0.1", "0.0.0.0"}:
        raise ValueError("BIND_HOST must be 127.0.0.1 or 0.0.0.0")
    if not 1 <= PORT <= 65535:
        raise ValueError("PORT must be in [1, 65535]")
    server = ThreadingHTTPServer((BIND_HOST, PORT), Handler)

    def stop(_signum: int, _frame: object) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(
        json.dumps(
            {
                "event": "server_started",
                "bind_host": BIND_HOST,
                "port": PORT,
                "version": VERSION,
                "fault_mode": FAULT_MODE,
                "ready_delay_seconds": READY_DELAY_SECONDS,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    server.serve_forever()
    server.server_close()
    print(json.dumps({"event": "server_stopped"}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
