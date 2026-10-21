#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(directory, name):
    path = directory / name
    if not path.is_file():
        raise SystemExit(f"[fail] missing {path}")
    return json.loads(path.read_text(encoding="utf-8"))


directory = Path(sys.argv[1] if len(sys.argv) > 1 else "results")
one = load(directory, "memory-7b.json")
eight = load(directory, "memory-7b-8seq.json")
benchmark = load(directory, "benchmark-cpu.json")

assert abs(one["memory_gib"]["raw_weights"] - 13.0385) < 0.01
print("[ok] 7B FP16 weight calculation is approximately 13.04 GiB")

ratio = eight["memory_gib"]["kv_cache"] / one["memory_gib"]["kv_cache"]
assert abs(ratio - 8) < 1e-9
print("[ok] KV cache grows linearly with sequence count")

assert benchmark["matmul"]["median_ms"] > 0
assert benchmark["matmul"]["approx_gflops"] > 0
assert benchmark["copy"]["median_ms"] > 0
assert benchmark["copy"]["approx_gigabytes_per_second"] > 0
print("[ok] benchmark timings and rates are positive")
print("All lesson 02 result checks passed.")
