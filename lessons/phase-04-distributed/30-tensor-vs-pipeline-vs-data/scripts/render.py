#!/usr/bin/env python3
"""Render DP and Ray model-parallel manifests from one frozen profile."""

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
    "__SERVED_MODEL__": required("SERVED_MODEL_NAME"),
    "__CACHE_SIZE__": required("MODEL_CACHE_GIB"),
    "__MAX_MODEL_LEN__": required("MAX_MODEL_LEN"),
    "__MAX_NUM_SEQS__": required("MAX_NUM_SEQS"),
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
    raise SystemExit("VLLM_IMAGE must be digest-pinned")
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]+", values["__MODEL_ID__"]):
    raise SystemExit("invalid MODEL_ID")
if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", values["__MODEL_REVISION__"]):
    raise SystemExit("MODEL_REVISION must be immutable hexadecimal commit")
if not re.fullmatch(
    r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}",
    values["__SERVED_MODEL__"],
):
    raise SystemExit("invalid SERVED_MODEL_NAME")
if not values["__CACHE_SIZE__"].isdigit() or not 5 <= int(
    values["__CACHE_SIZE__"]
) <= 500:
    raise SystemExit("MODEL_CACHE_GIB must be an integer from 5 through 500")
for placeholder, environment_name, maximum in (
    ("__MAX_MODEL_LEN__", "MAX_MODEL_LEN", 1_000_000),
    ("__MAX_NUM_SEQS__", "MAX_NUM_SEQS", 100_000),
):
    value = values[placeholder]
    if not value.isdigit() or not 1 <= int(value) <= maximum:
        raise SystemExit(
            f"{environment_name} must be an integer from 1 through {maximum}"
        )
output_dir = ROOT / "artifacts" / "rendered"
output_dir.mkdir(parents=True, exist_ok=True)
for name in ("dp", "ray-model-parallel"):
    text = (ROOT / "k8s" / f"{name}.yaml.tpl").read_text()
    for key, value in values.items():
        text = text.replace(key, value)
    if re.search(r"__[A-Z0-9_]+__", text):
        raise SystemExit(f"unrendered placeholder in {name}")
    if re.search(
        r"(?m)^\s*(?:type:\s*(?:LoadBalancer|NodePort|ExternalName)|"
        r"host(?:Network|PID|IPC):\s*true|externalIPs:)",
        text,
    ):
        raise SystemExit(f"unsafe network setting in {name}")
    (output_dir / f"{name}.yaml").write_text(text, encoding="utf-8")
    print(f"rendered {output_dir / f'{name}.yaml'}")
