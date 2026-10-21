#!/usr/bin/env python3
"""Render the vLLM PP=3 RayCluster after profile validation."""

from __future__ import annotations

import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise SystemExit(f"set {name}")
    return value


values = {
    "__NAMESPACE__": required("LAB_NAMESPACE"),
    "__NODEGROUP__": required("GPU_NODEGROUP"),
    "__VLLM_IMAGE__": required("VLLM_IMAGE"),
    "__MODEL_ID__": required("MODEL_ID"),
    "__MODEL_REVISION__": required("MODEL_REVISION"),
    "__CACHE_SIZE__": required("MODEL_CACHE_GIB"),
}
if not re.fullmatch(
    r"oms-distributed-[a-z0-9]([-a-z0-9]*[a-z0-9])?",
    values["__NAMESPACE__"],
) or len(values["__NAMESPACE__"]) > 63:
    raise SystemExit("invalid LAB_NAMESPACE")
if not re.fullmatch(
    r"[A-Za-z0-9][A-Za-z0-9_.-]{0,62}", values["__NODEGROUP__"]
):
    raise SystemExit("invalid GPU_NODEGROUP")
if not re.fullmatch(
    r"[A-Za-z0-9./:_-]+@sha256:[0-9a-f]{64}",
    values["__VLLM_IMAGE__"],
):
    raise SystemExit("VLLM_IMAGE must use an immutable sha256 digest")
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]+", values["__MODEL_ID__"]):
    raise SystemExit("invalid MODEL_ID")
if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", values["__MODEL_REVISION__"]):
    raise SystemExit("invalid MODEL_REVISION")
if not values["__CACHE_SIZE__"].isdigit() or not 5 <= int(
    values["__CACHE_SIZE__"]
) <= 500:
    raise SystemExit("MODEL_CACHE_GIB must be an integer from 5 through 500")

text = (ROOT / "k8s" / "vllm-pp-raycluster.yaml.tpl").read_text()
for key, value in values.items():
    text = text.replace(key, value)
if re.search(r"__[A-Z0-9_]+__", text):
    raise SystemExit("unrendered placeholder")
if re.search(
    r"(?m)^\s*(?:type:\s*(?:LoadBalancer|NodePort|ExternalName)|"
    r"host(?:Network|PID|IPC):\s*true|externalIPs:)",
    text,
):
    raise SystemExit("unsafe network setting")
output = ROOT / "artifacts" / "vllm-pp-raycluster.yaml"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(text)
print(f"rendered {output}")
