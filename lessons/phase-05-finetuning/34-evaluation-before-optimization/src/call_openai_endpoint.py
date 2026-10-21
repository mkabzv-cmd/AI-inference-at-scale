#!/usr/bin/env python3
"""Call an OpenAI-compatible chat endpoint using the frozen decoding config."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--acceptance", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=120)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    decoding = config["decoding"]
    endpoint = args.base_url.rstrip("/") + "/v1/chat/completions"
    api_key = os.environ.get("OPENAI_API_KEY", "not-required")
    predictions = []

    for item in read_jsonl(args.acceptance):
        payload = {
            "model": args.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Answer concisely. Do not invent cluster state. "
                        "Explain the evidence needed before making changes."
                    ),
                },
                {"role": "user", "content": item["prompt"]},
            ],
            "temperature": decoding["temperature"],
            "top_p": decoding["top_p"],
            "max_tokens": decoding["max_tokens"],
            "seed": decoding["seed"],
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(
                request,
                timeout=args.timeout_seconds,
            ) as response:
                document = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise SystemExit(
                f"{item['id']}: HTTP {error.code}: {body[:500]}"
            ) from error
        elapsed = time.perf_counter() - started
        predictions.append(
            {
                "id": item["id"],
                "response": document["choices"][0]["message"]["content"],
                "latency_seconds": elapsed,
                "model_returned": document.get("model"),
                "usage": document.get("usage"),
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for item in predictions:
            handle.write(json.dumps(item, sort_keys=True) + "\n")
    print(f"wrote {len(predictions)} predictions to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
