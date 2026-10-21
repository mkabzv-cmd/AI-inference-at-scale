#!/usr/bin/env python3
import json
import statistics
import sys
from pathlib import Path


def load(path: Path):
    if not path.is_file():
        raise SystemExit(f"[fail] missing result: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


result_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "results")
greedy = load(result_dir / "greedy.json")
sample_a = load(result_dir / "sample-a.json")
sample_b = load(result_dir / "sample-b.json")

trace = greedy["generation"]["trace"]
assert trace, "greedy trace is empty"
assert trace[0]["phase"] == "prefill"
assert trace[0]["model_input_tokens"] == greedy["prompt"]["token_count"]
decode_steps = [step for step in trace[1:] if step["phase"] == "decode"]
assert decode_steps, "expected at least one decode step"
assert all(step["model_input_tokens"] == 1 for step in decode_steps)
print("[ok] greedy result has prefill and cached decode")

assert greedy["comparison"]["token_ids_match"] is True
print("[ok] manual greedy output matches high-level output")

ids_a = sample_a["generation"]["generated_token_ids"]
ids_b = sample_b["generation"]["generated_token_ids"]
assert ids_a == ids_b
print("[ok] fixed-seed sampling is reproducible")

decode_ms = [step["forward_ms"] for step in decode_steps]
print(f"[info] median measured decode forward: {statistics.median(decode_ms):.3f} ms")
print("All lesson 01 result checks passed.")
