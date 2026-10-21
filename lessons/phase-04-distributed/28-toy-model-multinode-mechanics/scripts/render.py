#!/usr/bin/env python3
"""Render the three-node toy TP manifest."""

from __future__ import annotations

import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
values = {
    "__NAMESPACE__": os.environ.get("LAB_NAMESPACE", ""),
    "__NODEGROUP__": os.environ.get("GPU_NODEGROUP", ""),
    "__PYTORCH_IMAGE__": os.environ.get("PYTORCH_IMAGE", ""),
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
    values["__PYTORCH_IMAGE__"],
):
    raise SystemExit("PYTORCH_IMAGE must use @sha256")
text = (ROOT / "k8s" / "toy-tp.yaml.tpl").read_text(encoding="utf-8")
for key, value in values.items():
    text = text.replace(key, value)
if re.search(r"__[A-Z0-9_]+__", text):
    raise SystemExit("unrendered placeholder")
if re.search(
    r"(?m)^\s*(?:type:\s*(?:LoadBalancer|NodePort|ExternalName)|"
    r"host(?:Network|PID|IPC):\s*true|externalIPs:)",
    text,
):
    raise SystemExit("unsafe network setting in rendered manifest")
output = ROOT / "artifacts" / "toy-tp.yaml"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(text, encoding="utf-8")
print(f"rendered {output}")
