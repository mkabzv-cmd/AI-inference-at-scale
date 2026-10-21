#!/usr/bin/env python3
"""Small streaming OpenAI-compatible benchmark with correctness checks.

This is intentionally auditable and dependency-free. Lesson 12's richer
benchmark tooling remains preferable for production-grade load generation.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import platform
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = (len(ordered) - 1) * probability
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def invoke(
    base_url: str,
    model: str,
    prompt: dict[str, Any],
    sampling: dict[str, Any],
    timeout: float,
    request_id: str,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]},
        ],
        **sampling,
        "stream_options": {"include_usage": True},
    }
    request = urllib.request.Request(
        base_url.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    first_content = None
    previous_content = None
    inter_token_like_ms = []
    chunks = []
    usage: dict[str, Any] = {}
    status = 0
    finish_reason = None
    error = None
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data: "):
                    continue
                body = line[6:]
                if body == "[DONE]":
                    break
                event = json.loads(body)
                usage = event.get("usage") or usage
                choices = event.get("choices") or []
                if choices:
                    choice = choices[0]
                    finish_reason = choice.get("finish_reason") or finish_reason
                    content = choice.get("delta", {}).get("content")
                    if content:
                        now = time.perf_counter()
                        if first_content is None:
                            first_content = now
                        elif previous_content is not None:
                            inter_token_like_ms.append(
                                (now - previous_content) * 1000
                            )
                        previous_content = now
                        chunks.append(content)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        error = f"{type(exc).__name__}: {exc}"
    end = time.perf_counter()
    text = "".join(chunks)
    output_token_count = usage.get("completion_tokens")
    e2e_ms = (end - start) * 1000
    ttft_ms = (
        (first_content - start) * 1000 if first_content is not None else None
    )
    tpot_ms = (
        (e2e_ms - ttft_ms) / (output_token_count - 1)
        if ttft_ms is not None
        and isinstance(output_token_count, int)
        and output_token_count > 1
        else None
    )
    return {
        "request_id": request_id,
        "prompt_id": prompt["id"],
        "status_code": status,
        "e2e_ms": e2e_ms,
        "client_e2e_ms": e2e_ms,
        "queue_ms": None,
        "ttft_ms": ttft_ms,
        "tpot_ms": tpot_ms,
        "itl_ms": [],
        "stream_chunk_intervals_ms": inter_token_like_ms,
        "input_tokens": usage.get("prompt_tokens"),
        "output_tokens": output_token_count,
        "finish_reason": finish_reason,
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "quality_pass": (
            status == 200
            and prompt["required_substring"].casefold() in text.casefold()
        ),
        "error": error,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workload", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--model", default="oms-model")
    parser.add_argument("--engine-image-digest", required=True)
    parser.add_argument("--engine-version", required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9./:_-]*@sha256:[0-9a-f]{64}",
        args.engine_image_digest,
    ):
        parser.error(
            "--engine-image-digest must be an immutable name@sha256 digest"
        )
    if not re.fullmatch(
        r"[0-9]+(?:\.[0-9]+){1,3}(?:[A-Za-z0-9.+-]*)?",
        args.engine_version,
    ):
        parser.error("--engine-version must be the observed package version")
    if (
        not re.fullmatch(
            r"[a-z0-9]([-a-z0-9]*[a-z0-9])?",
            args.candidate_id,
        )
        or len(args.candidate_id) > 63
    ):
        parser.error("--candidate-id must be a Kubernetes-safe name")
    workload = json.loads(args.workload.read_text(encoding="utf-8"))
    prompts = workload["prompts"]
    sampling = workload["sampling"]
    timeout = float(workload["request_timeout_seconds"])

    for index in range(int(workload["warmup_requests"])):
        result = invoke(
            args.base_url,
            args.model,
            prompts[index % len(prompts)],
            sampling,
            timeout,
            f"warmup-{index}",
        )
        if result["status_code"] != 200:
            raise SystemExit(f"warmup failed: {result['error']}")

    started = datetime.now(timezone.utc).isoformat()
    count = int(workload["measured_requests"])
    wall_start = time.perf_counter()
    requests = []
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=int(workload["concurrency"])
    ) as executor:
        futures = [
            executor.submit(
                invoke,
                args.base_url,
                args.model,
                prompts[index % len(prompts)],
                sampling,
                timeout,
                f"measure-{index}",
            )
            for index in range(count)
        ]
        for future in concurrent.futures.as_completed(futures):
            requests.append(future.result())
    wall_seconds = time.perf_counter() - wall_start
    requests.sort(key=lambda item: item["request_id"])
    successes = [item for item in requests if item["status_code"] == 200]
    ttft = [item["ttft_ms"] for item in successes if item["ttft_ms"] is not None]
    e2e = [item["e2e_ms"] for item in successes]
    output_tokens = [
        item["output_tokens"]
        for item in successes
        if isinstance(item["output_tokens"], int)
    ]
    tpot = [
        item["tpot_ms"]
        for item in successes
        if item["tpot_ms"] is not None
    ]
    prompt_hash = hashlib.sha256(
        json.dumps(
            prompts, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    result = {
        "schema_version": "oms-benchmark/v1",
        "run_id": f"lesson23-{args.candidate_id}",
        "started_at_utc": started,
        "engine": {
            "name": "vllm",
            "version": args.engine_version,
            "config": {
                "image_digest": args.engine_image_digest,
                "candidate_id": args.candidate_id,
            },
        },
        "model": {
            "id": "Qwen/Qwen2.5-0.5B-Instruct",
            "revision": "7ae557604adf67be50417f59c2c2f167def9a775",
            "artifact": "huggingface-repository",
            "served_name": args.model,
        },
        "environment": {
            "client": {
                "python": sys.version.split()[0],
                "platform": platform.platform(),
            },
            "server": {
                "base_url": args.base_url,
            },
            "gpu": {
                "collected_separately": True,
            },
        },
        "workload": {
            **workload,
            "prompt_set_hash": prompt_hash,
        },
        "requests": requests,
        "summary": {
            "success_rate": len(successes) / len(requests),
            "quality_pass_rate": (
                sum(item["quality_pass"] for item in requests) / len(requests)
            ),
            "request_throughput_rps": len(successes) / wall_seconds,
            "output_throughput_tokens_per_second": (
                sum(output_tokens) / wall_seconds if output_tokens else None
            ),
            "ttft_p50_ms": percentile(ttft, 0.50),
            "ttft_p95_ms": percentile(ttft, 0.95),
            "tpot_p50_ms": percentile(tpot, 0.50),
            "tpot_p95_ms": percentile(tpot, 0.95),
            "e2e_p50_ms": percentile(e2e, 0.50),
            "e2e_p95_ms": percentile(e2e, 0.95),
            "e2e_mean_ms": statistics.mean(e2e) if e2e else None,
            "wall_seconds": wall_seconds,
        },
        "measurement_notes": {
            "queue_ms": "not observable from the external client",
            "itl_ms": (
                "left empty because SSE chunks are not guaranteed to be one "
                "token; tpot_ms is derived from usage token counts"
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))
    return 0 if len(successes) == len(requests) else 4


if __name__ == "__main__":
    raise SystemExit(main())
