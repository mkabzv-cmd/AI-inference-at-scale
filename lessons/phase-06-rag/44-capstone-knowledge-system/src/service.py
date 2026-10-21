#!/usr/bin/env python3
"""Private-by-default standard-library knowledge-service API."""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

LESSON = Path(__file__).resolve().parents[1]
PHASE = LESSON.parent
L41 = PHASE / "41-ingestion-chunks-embeddings-indexes"
L42 = PHASE / "42-retrieval-hybrid-reranking"
L43 = PHASE / "43-grounded-generation-rag-evaluation-security"
sys.path.insert(0, str(L41 / "src"))
sys.path.insert(0, str(L42 / "src"))
sys.path.insert(0, str(L43 / "src"))

from grounding import GroundedSystem  # noqa: E402
from rag_ingest import build  # noqa: E402


class Metrics:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.requests = 0
        self.abstentions = 0
        self.errors = 0

    def observe(self, abstained: bool = False, error: bool = False) -> None:
        with self.lock:
            self.requests += 1
            self.abstentions += int(abstained)
            self.errors += int(error)

    def render(self, source_sha256: str) -> str:
        with self.lock:
            values = (self.requests, self.abstentions, self.errors)
        return "\n".join(
            [
                "# HELP knowledge_requests_total Query requests received.",
                "# TYPE knowledge_requests_total counter",
                f"knowledge_requests_total {values[0]}",
                "# HELP knowledge_abstentions_total Query responses that abstained.",
                "# TYPE knowledge_abstentions_total counter",
                f"knowledge_abstentions_total {values[1]}",
                "# HELP knowledge_errors_total Query requests rejected or failed.",
                "# TYPE knowledge_errors_total counter",
                f"knowledge_errors_total {values[2]}",
                "# HELP knowledge_index_info Active immutable source snapshot.",
                "# TYPE knowledge_index_info gauge",
                f'knowledge_index_info{{source_sha256="{source_sha256}"}} 1',
                "",
            ]
        )


class KnowledgeApplication:
    def __init__(self) -> None:
        phase_override = os.environ.get("COURSE_PHASE_DIR")
        self.phase = Path(phase_override).resolve() if phase_override else PHASE
        l41 = self.phase / "41-ingestion-chunks-embeddings-indexes"
        corpus_root = (l41 / "data").resolve()
        corpus_relative = os.environ.get(
            "COURSE_CORPUS_RELATIVE", "data/corpus-v1.jsonl"
        )
        self.corpus = (l41 / corpus_relative).resolve()
        try:
            self.corpus.relative_to(corpus_root)
        except ValueError as error:
            raise ValueError(
                "configured corpus must remain inside lesson 41 data"
            ) from error
        self.index_dir = Path(
            os.environ.get("COURSE_INDEX_DIR", "/tmp/course-knowledge-index")
        )
        self.identities_path = Path(
            os.environ.get(
                "COURSE_IDENTITIES_PATH", str(LESSON / "configs/identities.json")
            )
        )
        l42 = self.phase / "42-retrieval-hybrid-reranking"
        l43 = self.phase / "43-grounded-generation-rag-evaluation-security"
        self.manifest = build(
            self.corpus, l41 / "configs/pipeline.json", self.index_dir
        )
        identities = json.loads(self.identities_path.read_text())
        self.principals = {
            name: value["tenant_id"]
            for name, value in identities["principals"].items()
        }
        self.system = GroundedSystem(
            self.index_dir,
            json.loads((l42 / "configs/retrieval.json").read_text()),
            json.loads((l43 / "configs/grounding.json").read_text()),
        )
        self.metrics = Metrics()
        self.ready = True

    @property
    def source_sha256(self) -> str:
        return self.manifest["source"]["sha256"]

    def query(self, principal: str, question: str) -> dict[str, Any]:
        tenant_id = self.principals.get(principal)
        if tenant_id is None:
            raise PermissionError("unknown course principal")
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must be a non-empty string")
        if len(question) > 2000:
            raise ValueError("question exceeds 2000 characters")
        result = self.system.answer(question.strip(), tenant_id)
        self.metrics.observe(abstained=bool(result["abstained"]))
        return {
            "request_id": str(uuid.uuid4()),
            "principal": principal,
            "tenant_id": tenant_id,
            "index": {
                "source_file": self.corpus.name,
                "source_sha256": self.source_sha256,
            },
            "result": result,
        }


def handler_for(application: KnowledgeApplication):
    class Handler(BaseHTTPRequestHandler):
        server_version = "CourseKnowledgeService/1"

        def send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = (json.dumps(payload, sort_keys=True) + "\n").encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/healthz":
                self.send_json(HTTPStatus.OK, {"status": "ok"})
                return
            if self.path == "/readyz":
                status = HTTPStatus.OK if application.ready else HTTPStatus.SERVICE_UNAVAILABLE
                self.send_json(
                    status,
                    {
                        "ready": application.ready,
                        "source_sha256": application.source_sha256,
                    },
                )
                return
            if self.path == "/metrics":
                body = application.metrics.render(application.source_sha256).encode()
                self.send_response(HTTPStatus.OK)
                self.send_header(
                    "Content-Type", "text/plain; version=0.0.4; charset=utf-8"
                )
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self) -> None:
            if self.path != "/v1/query":
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 16_384:
                    raise ValueError("request body size is invalid")
                payload = json.loads(self.rfile.read(length))
                if set(payload) != {"question"}:
                    raise ValueError("request object must contain only question")
                principal = self.headers.get("X-Course-Principal", "")
                result = application.query(principal, payload["question"])
                self.send_json(HTTPStatus.OK, result)
            except PermissionError as error:
                application.metrics.observe(error=True)
                self.send_json(HTTPStatus.FORBIDDEN, {"error": str(error)})
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                application.metrics.observe(error=True)
                self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            except Exception:
                application.metrics.observe(error=True)
                self.send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": "internal request failure"},
                )

        def log_message(self, format_string: str, *args: Any) -> None:
            message = {
                "event": "http_access",
                "client": self.client_address[0],
                "method": self.command,
                "path": self.path,
                "status": args[1] if len(args) > 1 else "unknown",
                "time_unix": int(time.time()),
            }
            print(json.dumps(message, sort_keys=True), flush=True)

    return Handler


def main() -> int:
    host = os.environ.get("COURSE_HOST", "127.0.0.1")
    port = int(os.environ.get("COURSE_PORT", "8080"))
    application = KnowledgeApplication()
    server = ThreadingHTTPServer((host, port), handler_for(application))

    def shutdown(_signum: int, _frame: Any) -> None:
        application.ready = False
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    print(
        json.dumps(
            {
                "event": "service_ready",
                "host": host,
                "port": port,
                "source_sha256": application.source_sha256,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    server.serve_forever()
    server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
