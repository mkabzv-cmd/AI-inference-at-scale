#!/usr/bin/env python3
"""Dependency-free deterministic server for testing the benchmark client on CPU."""

from __future__ import annotations

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def send_json(self, data: object) -> None:
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/v1/models":
            self.send_json({"object": "list", "data": [{"id": "course-model"}]})
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        length = int(self.headers.get("content-length", "0"))
        json.loads(self.rfile.read(length))
        pieces = ["Model ", "serving ", "uses ", "tokens ", "and ", "a cache."]
        events = []
        for piece in pieces:
            events.append(
                "data: "
                + json.dumps(
                    {
                        "choices": [
                            {
                                "delta": {"content": piece},
                                "finish_reason": None,
                            }
                        ]
                    }
                )
                + "\n\n"
            )
        events.append(
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'
        )
        events.append("data: [DONE]\n\n")
        body = "".join(events).encode()
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        for event in events:
            self.wfile.write(event.encode())
            self.wfile.flush()
            time.sleep(0.01)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 18000), Handler).serve_forever()
