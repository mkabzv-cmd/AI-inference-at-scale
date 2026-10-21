#!/usr/bin/env python3
"""Generate synthetic contract fixtures and test verification/aggregation code."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


engines = ["transformers", "vllm", "sglang", "llama-cpp"]
workloads = [
    ("closed", 1, None, 24),
    ("closed", 4, None, 24),
    ("closed", 16, None, 24),
    ("open", 64, 4.0, 40),
]
prompt_hash = hashlib.sha256(
    Path("../12-benchmarking-methodology/bench/prompts.jsonl").read_bytes()
).hexdigest()

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary) / "raw"
    for engine_index, engine in enumerate(engines):
        engine_dir = root / engine
        engine_dir.mkdir(parents=True)
        for mode, concurrency, request_rate, measured in workloads:
            for repeat in range(3):
                latency = 100.0 + engine_index * 10 + repeat
                measured_requests = [
                    {
                        "request_id": f"{engine}-{index}",
                        "prompt_id": "self-test",
                        "status_code": 200,
                        "e2e_ms": latency,
                        "ttft_ms": latency / 4,
                        "inter_token_latency_ms": [5.0],
                        "input_tokens": 10,
                        "output_tokens": 8,
                        "finish_reason": "stop",
                        "text_sha256": "0" * 64,
                        "quality_pass": True,
                        "quality_reasons": [],
                        "error": None,
                        "warmup": False,
                    }
                    for index in range(measured)
                ]
                warmup_requests = [
                    {
                        **measured_requests[index % len(measured_requests)],
                        "request_id": f"{engine}-warmup-{index}",
                        "warmup": True,
                    }
                    for index in range(3)
                ]
                requests = warmup_requests + measured_requests
                data = {
                    "schema_version": "oms-benchmark/v1",
                    "run_id": f"self-{engine}-{mode}-{concurrency}-{repeat}",
                    "started_at_utc": "2026-10-21T00:00:00+00:00",
                    "engine": {"name": engine, "version": "self-test", "config": {}},
                    "model": {
                        "id": "Qwen/Qwen2.5-0.5B-Instruct",
                        "revision": "7ae557604adf67be50417f59c2c2f167def9a775",
                        "artifact": "self-test",
                    },
                    "environment": {
                        "gpu_name": "synthetic-gpu",
                        "server_fingerprint": "synthetic",
                    },
                    "workload": {
                        "mode": mode,
                        "concurrency": concurrency,
                        "request_rate": request_rate,
                        "warmup_requests": 3,
                        "measured_requests": measured,
                        "prompt_set_sha256": prompt_hash,
                        "max_tokens": 64,
                        "temperature": 0.0,
                        "seed": 42,
                        "stream": True,
                        "tokenizer_mode": "hf",
                    },
                    "requests": requests,
                    "summary": {
                        "measured_requests": measured,
                        "successful_requests": measured,
                        "success_rate": 1.0,
                        "quality_pass_rate": 1.0,
                        "measurement_window_seconds": 1.0,
                        "request_throughput_per_second": measured,
                        "output_token_throughput_per_second": measured * 8,
                        "latency_ms": {"p50": latency, "p95": latency},
                        "ttft_ms": {"p50": latency / 4, "p95": latency / 4},
                        "itl_ms": {"p50": 5.0, "p95": 5.0},
                        "tpot_ms": {"p50": 5.0, "p95": 5.0},
                    },
                }
                name = f"{mode}-c{concurrency}-r{repeat}.json"
                (engine_dir / name).write_text(json.dumps(data))
    subprocess.run(
        ["python3", "scripts/verify_study.py", str(root)], check=True
    )
    subprocess.run(
        [
            "python3",
            "scripts/compare.py",
            str(root),
            "--json-output",
            str(Path(temporary) / "comparison.json"),
            "--markdown-output",
            str(Path(temporary) / "report.md"),
        ],
        check=True,
    )
    assert (Path(temporary) / "report.md").read_text().startswith(
        "# Controlled engine comparison"
    )
    victim = next(root.glob("*/*.json"))
    contaminated = json.loads(victim.read_text())
    contaminated["workload"]["measured_requests"] = 1
    victim.write_text(json.dumps(contaminated))
    rejected = subprocess.run(
        ["python3", "scripts/verify_study.py", str(root)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert rejected.returncode != 0, (
        "verifier accepted a run outside the frozen request-count matrix"
    )
    print("changed request count correctly rejected")
print("capstone CPU contract self-test passed")
