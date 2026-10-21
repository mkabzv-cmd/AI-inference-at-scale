#!/usr/bin/env python3
"""Render the three-rank manifest with narrowly validated values."""

from __future__ import annotations

import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "artifacts" / "rendered.yaml"


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise SystemExit(f"set {name}")
    return value


values = {
    "__NAMESPACE__": required("LAB_NAMESPACE"),
    "__NODEGROUP__": required("GPU_NODEGROUP"),
    "__PYTORCH_IMAGE__": required("PYTORCH_IMAGE"),
}
if not re.fullmatch(
    r"oms-distributed-[a-z0-9]([-a-z0-9]*[a-z0-9])?",
    values["__NAMESPACE__"],
) or len(values["__NAMESPACE__"]) > 63:
    raise SystemExit("LAB_NAMESPACE must begin oms-distributed-")
if not re.fullmatch(
    r"[A-Za-z0-9][A-Za-z0-9_.-]{0,62}", values["__NODEGROUP__"]
):
    raise SystemExit("GPU_NODEGROUP contains unsupported characters")
if not re.fullmatch(
    r"[A-Za-z0-9./:_-]+@sha256:[0-9a-f]{64}",
    values["__PYTORCH_IMAGE__"],
):
    raise SystemExit(
        "PYTORCH_IMAGE must be a complete immutable digest reference"
    )

text = (ROOT / "k8s" / "collectives.yaml.tpl").read_text(
    encoding="utf-8"
)
for placeholder, value in values.items():
    text = text.replace(placeholder, value)
if re.search(r"__[A-Z0-9_]+__", text):
    raise SystemExit("unrendered placeholder remains")
if re.search(
    r"(?m)^\s*(?:type:\s*(?:LoadBalancer|NodePort|ExternalName)|"
    r"host(?:Network|PID|IPC):\s*true|externalIPs:)",
    text,
):
    raise SystemExit("rendered manifest violates network safety policy")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(text, encoding="utf-8")
print(f"rendered {OUTPUT}")
