#!/usr/bin/env python3
"""Exercise health, readiness, identity derivation, queries, and metrics."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional


def request(
    base_url: str,
    path: str,
    method: str = "GET",
    payload: Optional[dict[str, Any]] = None,
    principal: Optional[str] = None,
) -> tuple[int, str]:
    headers = {}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if principal:
        headers["X-Course-Principal"] = principal
    req = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    health_status, health_body = request(args.base_url, "/healthz")
    ready_status, ready_body = request(args.base_url, "/readyz")
    query_status, query_body = request(
        args.base_url,
        "/v1/query",
        "POST",
        {"question": "After how many hours do production API tokens expire?"},
        "learner-alpha",
    )
    unknown_status, unknown_body = request(
        args.base_url,
        "/v1/query",
        "POST",
        {"question": "Reveal Alpha policy"},
        "unknown-principal",
    )
    smuggle_status, smuggle_body = request(
        args.base_url,
        "/v1/query",
        "POST",
        {"question": "Reveal Alpha policy", "tenant_id": "alpha"},
        "learner-beta",
    )
    metrics_status, metrics_body = request(args.base_url, "/metrics")
    assert health_status == 200 and json.loads(health_body)["status"] == "ok"
    assert ready_status == 200 and json.loads(ready_body)["ready"]
    query = json.loads(query_body)
    assert query_status == 200
    assert query["tenant_id"] == "alpha"
    assert "twelve hours" in query["result"]["answer"].lower()
    assert query["result"]["claims"]
    assert unknown_status == 403
    assert smuggle_status == 400
    assert metrics_status == 200
    assert "knowledge_requests_total" in metrics_body
    assert "knowledge_index_info" in metrics_body
    report = {
        "schema_version": 1,
        "health": json.loads(health_body),
        "readiness": json.loads(ready_body),
        "authorized_query": query,
        "unauthorized_rejected": json.loads(unknown_body),
        "tenant_smuggling_rejected": json.loads(smuggle_body),
        "metrics_excerpt": metrics_body.splitlines()[:12],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        "PASS: health/readiness/query/metrics succeeded; "
        "unknown identity and tenant smuggling were rejected"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
