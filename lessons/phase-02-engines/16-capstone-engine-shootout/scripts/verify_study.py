#!/usr/bin/env python3
"""Fail closed when supposedly comparable benchmark files differ."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
from typing import Any


def workload_key(workload: dict[str, Any]) -> tuple[str, int, float | None]:
    return (
        workload["mode"],
        int(workload["concurrency"]),
        (
            float(workload["request_rate"])
            if workload["mode"] == "open"
            else None
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    study = json.loads(Path("config/study.json").read_text())
    prompt_path = Path(study["prompt_set"]).resolve()
    expected_prompt_hash = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    files = sorted(args.directory.glob("*/*.json"))
    if not files:
        raise SystemExit("no benchmark files found")
    data = [(path, json.loads(path.read_text())) for path in files]
    engines = {item["engine"]["name"] for _, item in data}
    required_engines = set(study["required_engines"])
    missing = required_engines - engines
    unexpected = engines - required_engines
    if missing and not args.allow_incomplete:
        raise SystemExit(f"missing required engines: {sorted(missing)}")
    if unexpected:
        raise SystemExit(f"unexpected engines: {sorted(unexpected)}")
    expected_workloads = {
        workload_key(item): item for item in study["workloads"]
    }
    failures = []
    groups: dict[tuple[str, tuple[str, int, float | None]], list[Path]] = (
        collections.defaultdict(list)
    )
    run_ids = []
    for path, item in data:
        run_ids.append(item["run_id"])
        if item["schema_version"] != study["schema_version"]:
            failures.append(f"{path}: wrong schema")
        if item["model"]["id"] != study["model_id"]:
            failures.append(f"{path}: wrong model id")
        if item["model"]["revision"] != study["model_revision"]:
            failures.append(f"{path}: wrong source-model revision")
        if item["workload"]["prompt_set_sha256"] != expected_prompt_hash:
            failures.append(f"{path}: wrong prompt-set hash")
        if item["workload"]["max_tokens"] != study["sampling"]["max_tokens"]:
            failures.append(f"{path}: wrong max_tokens")
        if item["workload"]["temperature"] != study["sampling"]["temperature"]:
            failures.append(f"{path}: wrong temperature")
        if item["workload"]["seed"] != study["sampling"]["seed"]:
            failures.append(f"{path}: wrong seed")
        if item["workload"]["stream"] != study["sampling"]["stream"]:
            failures.append(f"{path}: wrong stream setting")
        if item["workload"]["tokenizer_mode"] != "hf":
            failures.append(f"{path}: self-test tokenizer is forbidden")
        if item["summary"]["success_rate"] < study["minimum_success_rate"]:
            failures.append(f"{path}: success gate failed")
        if item["summary"]["quality_pass_rate"] < study["minimum_quality_pass_rate"]:
            failures.append(f"{path}: quality gate failed")
        workload = item["workload"]
        key = workload_key(workload)
        expected = expected_workloads.get(key)
        if expected is None:
            failures.append(f"{path}: workload is outside the frozen matrix")
        else:
            for field in ("warmup_requests", "measured_requests"):
                if workload[field] != expected[field]:
                    failures.append(
                        f"{path}: wrong {field} for workload {key}"
                    )
        if item["summary"]["measured_requests"] != workload["measured_requests"]:
            failures.append(f"{path}: summary/request-count mismatch")
        measured_records = [
            record for record in item["requests"] if not record["warmup"]
        ]
        warmup_records = [
            record for record in item["requests"] if record["warmup"]
        ]
        if len(measured_records) != workload["measured_requests"]:
            failures.append(f"{path}: measured record count mismatch")
        if len(warmup_records) != workload["warmup_requests"]:
            failures.append(f"{path}: warm-up record count mismatch")
        groups[(item["engine"]["name"], key)].append(path)
    if len(set(run_ids)) != len(run_ids):
        failures.append("duplicate run_id values found")
    for engine in sorted(engines):
        for key in expected_workloads:
            count = len(groups[(engine, key)])
            if count != study["repeat_count"]:
                failures.append(
                    f"{engine} workload {key} has {count} repeats; "
                    f"expected exactly {study['repeat_count']}"
                )
    for engine in sorted(engines):
        engine_runs = [item for _, item in data if item["engine"]["name"] == engine]
        versions = {item["engine"]["version"] for item in engine_runs}
        configs = {
            json.dumps(
                item["engine"]["config"],
                sort_keys=True,
                separators=(",", ":"),
            )
            for item in engine_runs
        }
        fingerprints = {
            item["environment"]["server_fingerprint"]
            for item in engine_runs
        }
        if len(versions) != 1:
            failures.append(f"{engine}: engine version changed across runs")
        if len(configs) != 1:
            failures.append(f"{engine}: engine config changed across runs")
        if len(fingerprints) != 1:
            failures.append(f"{engine}: server fingerprint changed across runs")
    gpu_names = {item["environment"]["gpu_name"] for _, item in data}
    if len(gpu_names) != 1:
        failures.append(f"GPU hardware differs across runs: {sorted(gpu_names)}")
    if "record-from-server" in gpu_names:
        failures.append("placeholder GPU name remains")
    if any(
        item["environment"]["server_fingerprint"] == "record-me"
        for _, item in data
    ):
        failures.append("placeholder server fingerprint remains")
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"verified {len(files)} records across {len(engines)} engines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
