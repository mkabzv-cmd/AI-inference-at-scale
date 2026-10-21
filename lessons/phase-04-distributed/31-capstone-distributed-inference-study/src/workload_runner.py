#!/usr/bin/env python3
"""Run named completion cases and emit one raw capstone run."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import statistics
import time
from pathlib import Path
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--workload", type=Path, required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--repetition", type=int, required=True)
    parser.add_argument("--vllm-version", required=True)
    parser.add_argument("--ray-version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    allowed = {"data-parallel", "tensor-parallel", "pipeline-parallel"}
    if args.strategy not in allowed:
        raise SystemExit(f"strategy must be one of {sorted(allowed)}")
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    cases = [
        json.loads(line)
        for line in args.workload.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not cases:
        raise SystemExit("workload contains no cases")
    if any(
        not isinstance(case, dict)
        or not isinstance(case.get("case"), str)
        or not case["case"]
        or not isinstance(case.get("body"), dict)
        for case in cases
    ):
        raise SystemExit("each workload line needs a nonempty case and body object")
    if len({case["case"] for case in cases}) != len(cases):
        raise SystemExit("workload case names must be unique")
    payload_hash = hashlib.sha256(args.workload.read_bytes()).hexdigest()
    if payload_hash != spec["workload"]["sha256"]:
        raise SystemExit("workload bytes do not match frozen study SHA-256")
    if not 1 <= args.repetition <= spec["design"]["repeats"]:
        raise SystemExit("repetition outside frozen design")
    expected_versions = {
        "vLLM": (
            args.vllm_version,
            spec["software"]["vllm_expected_version"],
        ),
        "Ray": (
            args.ray_version,
            spec["software"]["ray_expected_version"],
        ),
    }
    for label, (observed, expected) in expected_versions.items():
        if observed != expected:
            raise SystemExit(
                f"observed {label} version {observed!r} differs from "
                f"frozen version {expected!r}"
            )

    def send(case: dict[str, object], measured: bool) -> dict[str, object]:
        body = json.dumps(case["body"], separators=(",", ":")).encode()
        request = Request(
            args.url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = time.perf_counter()
        with urlopen(request, timeout=180) as response:
            document = json.load(response)
        elapsed = time.perf_counter() - started
        text = document["choices"][0]["text"]
        return {
            "case": case["case"],
            "measured": measured,
            "elapsed_seconds": elapsed,
            "correct": bool(text) and document.get("object") == "text_completion",
            "completion_tokens": document.get("usage", {}).get(
                "completion_tokens", 0
            ),
        }

    for case in cases:
        send(case, measured=False)
    concurrency = spec["workload"]["concurrency"]
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=concurrency
    ) as pool:
        records = list(pool.map(lambda case: send(case, True), cases))
    wall = time.perf_counter() - started
    latencies = [float(record["elapsed_seconds"]) for record in records]
    passed = len(records) == len(cases) and all(
        record["correct"] for record in records
    )
    document = {
        "schema_version": 1,
        "experiment_id": (
            f"{spec['study_id']}-{args.strategy}-{args.repetition}"
        ),
        "study_id": spec["study_id"],
        "strategy": args.strategy,
        "repetition": args.repetition,
        "correctness": {"passed": passed},
        "environment": {
            "model_id": spec["model"]["id"],
            "model_revision": spec["model"]["revision"],
            "image_digest": spec["software"]["image_digest"],
            "workload_sha256": payload_hash,
            "request_count": len(cases),
            "concurrency": concurrency,
            "instance_type": spec["topology"]["instance_type"],
            "vllm_expected_version": spec["software"][
                "vllm_expected_version"
            ],
            "ray_expected_version": spec["software"]["ray_expected_version"],
            "vllm_observed_version": args.vllm_version,
            "ray_observed_version": args.ray_version,
            "max_model_len": spec["runtime"]["max_model_len"],
            "max_num_seqs": spec["runtime"]["max_num_seqs"],
            "model_cache_gib_per_node": spec["runtime"][
                "model_cache_gib_per_node"
            ],
        },
        "measurements": {
            "wall_seconds": wall,
            "requests_per_second": len(records) / wall,
            "median_end_to_end_seconds": statistics.median(latencies),
            "minimum_end_to_end_seconds": min(latencies),
            "maximum_end_to_end_seconds": max(latencies),
            "completion_tokens": sum(
                int(record["completion_tokens"]) for record in records
            ),
            "records": records,
        },
        "limitations": [
            "non-streaming request timing; TTFT and TPOT not measured",
            "small teaching workload",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output}; passed={passed}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
