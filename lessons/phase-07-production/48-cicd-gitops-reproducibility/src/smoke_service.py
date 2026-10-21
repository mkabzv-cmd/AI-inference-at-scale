#!/usr/bin/env python3
"""Loopback-only smoke service representing one immutable release."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


RELEASE: dict[str, object]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return

    def send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self.send_json(200, {"status": "ok"})
            return
        if self.path == "/release":
            self.send_json(
                200,
                {
                    "release_id": RELEASE["release_id"],
                    "image": RELEASE["image"],
                    "model_revision": RELEASE["model"]["revision"],
                    "index_version": RELEASE["index"]["version"],
                },
            )
            return
        self.send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self.send_json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        self.send_json(
            200,
            {
                "model": RELEASE["model"]["id"],
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": RELEASE["smoke_response"],
                        }
                    }
                ],
            },
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8048)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        parser.error("the teaching smoke service may bind only to loopback")
    global RELEASE
    RELEASE = json.loads(args.release.read_text(encoding="utf-8"))
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"listening=http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
