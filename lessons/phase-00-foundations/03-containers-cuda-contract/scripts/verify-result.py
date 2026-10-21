#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("result", type=Path)
parser.add_argument("--expect", choices=("gpu", "no-gpu"), required=True)
args = parser.parse_args()

record = json.loads(args.result.read_text(encoding="utf-8"))
if args.expect == "no-gpu":
    assert record["cuda_available"] is False
    assert record["visible_gpu_count"] == 0
    assert record["tensor_check"] is None
    print("[ok] result correctly reports no visible GPU")
else:
    assert record["cuda_available"] is True
    assert record["visible_gpu_count"] >= 1
    assert record["tensor_check"] == [11.0]
    assert record["tensor_error"] is None
    print("[ok] result contains a successful CUDA tensor check")
