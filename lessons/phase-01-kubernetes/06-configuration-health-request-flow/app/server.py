#!/usr/bin/env python3
"""Small dependency-free server for learning Kubernetes health and config."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


STARTED_AT = time.monotonic()
PORT = int(os.environ.get("PORT", "8080"))
BIND_HOST = os.environ.get("BIND_HOST", "127.0.0.1")
STARTUP_SECONDS = float(os.environ.get("STARTUP_SECONDS", "8"))
NOT_READY_FILE = Path("/tmp/lesson-not-ready")
NOT_LIVE_FILE = Path("/tmp/lesson-kill-liveness")
CONFIG_FILE = Path("/etc/lesson/config/message.txt")
TOKEN_FILE = Path("/var/run/secrets/lesson/api-token")


def elapsed_seconds() -> float:
    return time.monotonic() - STARTED_AT


def log(event: str, **fields: object) -> None:
    record = {
        "event": event,
        "elapsed_seconds": round(elapsed_seconds(), 3),
        **fields,
    }
    print(json.dumps(record, sort_keys=True), flush=True)


class Handler(BaseHTTPRequestHandler):
    server_version = "lesson-health-app/0.1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        log("http_access", client=self.client_address[0], message=fmt % args)

    def send_text(self, status: int, body: str, content_type: str = "text/plain") -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_json(self, status: int, value: object) -> None:
        self.send_text(status, json.dumps(value, indent=2) + "\n", "application/json")

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        path = urlparse(self.path).path

        if path == "/health/startup":
            if elapsed_seconds() >= STARTUP_SECONDS:
                self.send_text(200, "started\n")
            else:
                self.send_text(503, "still loading\n")
            return

        if path == "/health/ready":
            if elapsed_seconds() < STARTUP_SECONDS:
                self.send_text(503, "startup incomplete\n")
            elif NOT_READY_FILE.exists():
                self.send_text(503, "temporarily not ready\n")
            else:
                self.send_text(200, "ready\n")
            return

        if path == "/health/live":
            if NOT_LIVE_FILE.exists():
                self.send_text(500, "unrecoverable simulated failure\n")
            else:
                self.send_text(200, "alive\n")
            return

        if path == "/":
            self.send_json(
                200,
                {
                    "greeting": os.environ.get("APP_GREETING", "hello"),
                    "model": os.environ.get("MODEL_NAME", "unset"),
                    "pod": os.environ.get("HOSTNAME", "unknown"),
                    "uptime_seconds": round(elapsed_seconds(), 3),
                },
            )
            return

        if path == "/config":
            try:
                message = CONFIG_FILE.read_text(encoding="utf-8").strip()
            except OSError as error:
                self.send_json(500, {"error": str(error), "path": str(CONFIG_FILE)})
                return
            self.send_json(200, {"message_from_config_volume": message})
            return

        if path == "/secret-fingerprint":
            try:
                token = TOKEN_FILE.read_bytes()
            except OSError as error:
                self.send_json(500, {"error": str(error), "path": str(TOKEN_FILE)})
                return
            fingerprint = hashlib.sha256(token).hexdigest()[:12]
            self.send_json(200, {"sha256_prefix": fingerprint, "token_exposed": False})
            return

        if path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Connection", "close")
            self.end_headers()
            for number in range(1, 6):
                self.wfile.write(f"token-{number}\n".encode("utf-8"))
                self.wfile.flush()
                time.sleep(0.4)
            self.close_connection = True
            return

        self.send_json(404, {"error": "not found", "path": path})


def main() -> None:
    if BIND_HOST not in {"127.0.0.1", "0.0.0.0"}:
        raise ValueError("BIND_HOST must be 127.0.0.1 or 0.0.0.0")
    log(
        "server_starting",
        bind_host=BIND_HOST,
        port=PORT,
        startup_seconds=STARTUP_SECONDS,
        python=sys.version.split()[0],
    )
    server = ThreadingHTTPServer((BIND_HOST, PORT), Handler)
    log("server_listening", address=BIND_HOST, port=PORT)
    server.serve_forever()


if __name__ == "__main__":
    main()
