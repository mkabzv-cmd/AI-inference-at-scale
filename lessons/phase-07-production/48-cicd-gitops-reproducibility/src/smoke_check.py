#!/usr/bin/env python3
"""Behavioral and release-identity smoke checks."""

from __future__ import annotations

import argparse
import json
import urllib.request


def get_json(url: str) -> dict[str, object]:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--expected-release", required=True)
    args = parser.parse_args()
    failures = []

    health = get_json(args.base_url.rstrip("/") + "/healthz")
    release = get_json(args.base_url.rstrip("/") + "/release")
    request = urllib.request.Request(
        args.base_url.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(
            {
                "model": "smoke",
                "messages": [
                    {
                        "role": "user",
                        "content": "Why can a Running Pod be absent from endpoints?",
                    }
                ],
                "temperature": 0,
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        completion = json.loads(response.read().decode("utf-8"))
    answer = completion["choices"][0]["message"]["content"].lower()

    if health.get("status") != "ok":
        failures.append("health check failed")
    if release.get("release_id") != args.expected_release:
        failures.append("runtime release identity differs from candidate")
    required = {"readiness", "selector", "endpoints"}
    missing = sorted(term for term in required if term not in answer)
    if missing:
        failures.append(f"behavioral smoke missing concepts: {missing}")
    if "load balancer" in answer or "restart the cluster" in answer:
        failures.append("behavioral smoke contains forbidden unsafe advice")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(
        f"PASS: {args.expected_release} health, identity, and behavioral smoke "
        "checks passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
