#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


data = json.loads(
    Path(sys.argv[1] if len(sys.argv) > 1 else "artifacts/results.json")
    .read_text(encoding="utf-8")
)
if data["schema_version"] != "oms-reuse-lookahead/v1":
    raise SystemExit("unexpected schema")
prefix = {item["id"]: item for item in data["prefix_cache"]["requests"]}
if prefix["tenant-a-repeat"]["hit_blocks"] != 2:
    raise SystemExit("expected two complete shared blocks")
if prefix["tenant-b-same-text"]["hit_blocks"] != 0:
    raise SystemExit("tenant isolation failed")
spec = {
    item["name"]: item for item in data["speculative_decoding"]
}
if not all(item["output_exact_match"] for item in spec.values()):
    raise SystemExit("speculation changed target output")
if spec["useful-draft"]["acceptance_rate"] <= spec["poor-draft"]["acceptance_rate"]:
    raise SystemExit("useful draft should have higher acceptance")
if spec["useful-draft"]["target_verification_steps"] >= spec[
    "poor-draft"
]["target_verification_steps"]:
    raise SystemExit("useful draft should need fewer target verification steps")
chunking = {
    item["chunk_size"]: item for item in data["chunked_prefill"]
}
if chunking[64]["short_ttft_ticks"] <= chunking[16]["short_ttft_ticks"]:
    raise SystemExit("smaller chunks should help the supplied short request")
print("verified cache isolation, exact speculative output, and acceptance effect")
