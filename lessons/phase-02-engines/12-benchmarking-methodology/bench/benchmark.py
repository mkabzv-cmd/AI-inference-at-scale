#!/usr/bin/env python3
"""Small auditable OpenAI-chat benchmark for the course engine comparisons."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import platform
import socket
import statistics
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


SCHEMA_VERSION = "oms-benchmark/v1"
DEFAULT_MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
DEFAULT_MODEL_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"


class WhitespaceTokenizer:
    """Offline-only test double; never use it for reported model benchmarks."""

    def apply_chat_template(
        self, messages: list[dict[str, str]], tokenize: bool, add_generation_prompt: bool
    ) -> str:
        del tokenize
        text = "\n".join(f"{item['role']}: {item['content']}" for item in messages)
        return text + ("\nassistant:" if add_generation_prompt else "")

    def encode(self, text: str, add_special_tokens: bool) -> list[str]:
        del add_special_tokens
        return text.split()


@dataclass
class RequestRecord:
    request_id: str
    prompt_id: str
    scheduled_offset_ms: float
    client_start_offset_ms: float
    arrival_lag_ms: float
    status_code: int
    e2e_ms: float
    ttft_ms: float | None
    inter_token_latency_ms: list[float]
    input_tokens: int
    output_tokens: int
    finish_reason: str | None
    text_sha256: str
    quality_pass: bool
    quality_reasons: list[str]
    error: str | None
    warmup: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--prompts", type=Path, default=Path(__file__).with_name("prompts.jsonl"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--engine-name", required=True)
    parser.add_argument("--engine-version", required=True)
    parser.add_argument("--engine-config-json", default="{}")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--model-revision", default=DEFAULT_MODEL_REVISION)
    parser.add_argument("--served-model-name", default="course-model")
    parser.add_argument("--artifact", default="safetensors")
    parser.add_argument("--mode", choices=["closed", "open"], default="closed")
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--request-rate", type=float, default=1.0)
    parser.add_argument("--warmup-requests", type=int, default=2)
    parser.add_argument("--measured-requests", type=int, default=12)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument("--gpu-name", default=os.environ.get("BENCH_GPU_NAME", "record-from-server"))
    parser.add_argument("--server-fingerprint", default=os.environ.get("SERVER_FINGERPRINT", "record-me"))
    parser.add_argument(
        "--tokenizer-mode",
        choices=["hf", "whitespace-self-test"],
        default="hf",
        help="whitespace-self-test is only for the offline fake-server test",
    )
    args = parser.parse_args()
    if args.concurrency < 1 or args.measured_requests < 1 or args.warmup_requests < 0:
        parser.error("concurrency/measured requests must be positive; warmup cannot be negative")
    if args.mode == "open" and args.request_rate <= 0:
        parser.error("open-loop request rate must be positive")
    if args.max_tokens < 1:
        parser.error("max-tokens must be positive")
    return args


def load_prompts(path: Path) -> tuple[list[dict[str, Any]], str]:
    raw = path.read_bytes()
    prompts = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if not prompts:
        raise ValueError("prompt set is empty")
    for prompt in prompts:
        if not prompt.get("id") or not prompt.get("messages"):
            raise ValueError("each prompt needs id and messages")
    return prompts, hashlib.sha256(raw).hexdigest()


def percentile(values: list[float], percentage: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentage
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return round(ordered[lower], 3)
    weight = position - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 3)


def distribution(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "mean": round(statistics.fmean(values), 3) if values else None,
        "p50": percentile(values, 0.50),
        "p90": percentile(values, 0.90),
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
        "max": round(max(values), 3) if values else None,
    }


def quality_check(text: str, quality: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    normalized = text.casefold().strip()
    if len(text.strip()) < int(quality.get("min_chars", 1)):
        reasons.append("too_short")
    required = [str(item).casefold() for item in quality.get("required_any", [])]
    if required and not any(item in normalized for item in required):
        reasons.append("missing_required_concept")
    forbidden = [str(item).casefold() for item in quality.get("forbidden", [])]
    if any(item in normalized for item in forbidden):
        reasons.append("forbidden_phrase")
    return not reasons, reasons


async def one_request(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    prompt: dict[str, Any],
    tokenizer: Any,
    args: argparse.Namespace,
    run_started: float,
    scheduled_offset: float,
    warmup: bool,
) -> RequestRecord:
    if args.mode == "open":
        await asyncio.sleep(max(0.0, run_started + scheduled_offset - time.perf_counter()))
    async with semaphore:
        start = time.perf_counter()
        request_id = uuid.uuid4().hex
        input_text = tokenizer.apply_chat_template(
            prompt["messages"], tokenize=False, add_generation_prompt=True
        )
        input_tokens = len(tokenizer.encode(input_text, add_special_tokens=False))
        payload = {
            "model": args.served_model_name,
            "messages": prompt["messages"],
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
            "seed": args.seed,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        first_text_at: float | None = None
        previous_text_at: float | None = None
        itl: list[float] = []
        text_parts: list[str] = []
        finish_reason: str | None = None
        status = 0
        error: str | None = None
        try:
            async with client.stream(
                "POST", "/v1/chat/completions", json=payload
            ) as response:
                status = response.status_code
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:]
                    if raw == "[DONE]":
                        break
                    event = json.loads(raw)
                    if "error" in event:
                        raise RuntimeError(json.dumps(event["error"], sort_keys=True))
                    choices = event.get("choices", [])
                    if not choices:
                        continue
                    choice = choices[0]
                    finish_reason = choice.get("finish_reason") or finish_reason
                    piece = choice.get("delta", {}).get("content")
                    if not piece:
                        continue
                    now = time.perf_counter()
                    if first_text_at is None:
                        first_text_at = now
                    elif previous_text_at is not None:
                        itl.append((now - previous_text_at) * 1000)
                    previous_text_at = now
                    text_parts.append(piece)
        except Exception as caught:
            error = f"{type(caught).__name__}: {caught}"
        ended = time.perf_counter()
        text = "".join(text_parts)
        output_tokens = len(tokenizer.encode(text, add_special_tokens=False))
        passed, reasons = quality_check(text, prompt.get("quality", {}))
        if error:
            passed = False
            reasons.append("request_error")
        return RequestRecord(
            request_id=request_id,
            prompt_id=prompt["id"],
            scheduled_offset_ms=round(scheduled_offset * 1000, 3),
            client_start_offset_ms=round((start - run_started) * 1000, 3),
            arrival_lag_ms=round(max(0.0, start - run_started - scheduled_offset) * 1000, 3),
            status_code=status,
            e2e_ms=round((ended - start) * 1000, 3),
            ttft_ms=round((first_text_at - start) * 1000, 3) if first_text_at else None,
            inter_token_latency_ms=[round(value, 3) for value in itl],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason=finish_reason,
            text_sha256=hashlib.sha256(text.encode()).hexdigest(),
            quality_pass=passed,
            quality_reasons=reasons,
            error=error,
            warmup=warmup,
        )


async def execute(args: argparse.Namespace) -> dict[str, Any]:
    prompts, prompt_hash = load_prompts(args.prompts)
    if args.tokenizer_mode == "hf":
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(
            args.model_id,
            revision=args.model_revision,
            trust_remote_code=False,
        )
    else:
        tokenizer = WhitespaceTokenizer()
    semaphore = asyncio.Semaphore(args.concurrency)
    timeout = httpx.Timeout(args.timeout_seconds)
    async with httpx.AsyncClient(base_url=args.base_url.rstrip("/"), timeout=timeout) as client:
        health = await client.get("/v1/models")
        health.raise_for_status()
        # Warmup is complete before the measurement clock starts. Mixing warmup
        # with measured traffic would contaminate both latency and throughput.
        warmup_records = []
        warmup_started = time.perf_counter()
        for index in range(args.warmup_requests):
            warmup_records.append(
                await one_request(
                    client,
                    semaphore,
                    prompts[index % len(prompts)],
                    tokenizer,
                    args,
                    warmup_started,
                    0.0,
                    True,
                )
            )

        measurement_started = time.perf_counter()
        if args.mode == "open":
            measured_records = await asyncio.gather(
                *[
                    one_request(
                        client,
                        semaphore,
                        prompts[index % len(prompts)],
                        tokenizer,
                        args,
                        measurement_started,
                        index / args.request_rate,
                        False,
                    )
                    for index in range(args.measured_requests)
                ]
            )
        else:
            next_index = 0
            index_lock = asyncio.Lock()

            async def closed_loop_worker() -> list[RequestRecord]:
                nonlocal next_index
                output: list[RequestRecord] = []
                while True:
                    async with index_lock:
                        if next_index >= args.measured_requests:
                            return output
                        index = next_index
                        next_index += 1
                    # A closed-loop client sends its next request only after this
                    # awaited request completes.
                    output.append(
                        await one_request(
                            client,
                            semaphore,
                            prompts[index % len(prompts)],
                            tokenizer,
                            args,
                            measurement_started,
                            0.0,
                            False,
                        )
                    )
            worker_outputs = await asyncio.gather(
                *[
                    closed_loop_worker()
                    for _ in range(min(args.concurrency, args.measured_requests))
                ]
            )
            measured_records = [
                record for worker_output in worker_outputs for record in worker_output
            ]
    records = warmup_records + measured_records
    # Completion order is intentionally retained; request IDs make it unambiguous.
    measured = measured_records
    duration = max(
        record.client_start_offset_ms + record.e2e_ms for record in measured
    ) / 1000
    successful = [record for record in measured if record.status_code == 200 and not record.error]
    total_output = sum(record.output_tokens for record in successful)
    all_itl = [value for record in successful for value in record.inter_token_latency_ms]
    tpot = []
    for record in successful:
        if record.ttft_ms is not None and record.output_tokens > 1:
            tpot.append((record.e2e_ms - record.ttft_ms) / (record.output_tokens - 1))
    engine_config = json.loads(args.engine_config_json)
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": f"{args.engine_name}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "engine": {
            "name": args.engine_name,
            "version": args.engine_version,
            "config": engine_config,
        },
        "model": {
            "id": args.model_id,
            "revision": args.model_revision,
            "artifact": args.artifact,
        },
        "environment": {
            "client_python": sys.version.split()[0],
            "client_platform": platform.platform(),
            "client_hostname_hash": hashlib.sha256(socket.gethostname().encode()).hexdigest()[:12],
            "gpu_name": args.gpu_name,
            "server_fingerprint": args.server_fingerprint,
        },
        "workload": {
            "mode": args.mode,
            "concurrency": args.concurrency,
            "request_rate": args.request_rate if args.mode == "open" else None,
            "warmup_requests": args.warmup_requests,
            "measured_requests": args.measured_requests,
            "prompt_set_sha256": prompt_hash,
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
            "seed": args.seed,
            "stream": True,
            "tokenizer_mode": args.tokenizer_mode,
        },
        "requests": [asdict(record) for record in records],
        "summary": {
            "measured_requests": len(measured),
            "successful_requests": len(successful),
            "success_rate": round(len(successful) / len(measured), 6),
            "quality_pass_rate": round(
                sum(record.quality_pass for record in measured) / len(measured), 6
            ),
            "measurement_window_seconds": round(duration, 6),
            "request_throughput_per_second": round(len(successful) / duration, 6),
            "output_token_throughput_per_second": round(total_output / duration, 6),
            "latency_ms": distribution([record.e2e_ms for record in successful]),
            "ttft_ms": distribution(
                [record.ttft_ms for record in successful if record.ttft_ms is not None]
            ),
            "itl_ms": distribution(all_itl),
            "tpot_ms": distribution(tpot),
            "arrival_lag_ms": distribution([record.arrival_lag_ms for record in measured]),
        },
    }


def main() -> int:
    args = parse_args()
    result = asyncio.run(execute(args))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0 if result["summary"]["success_rate"] == 1.0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
