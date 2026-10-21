#!/usr/bin/env python3
"""Render the small teaching manifest without adding a template dependency."""

from __future__ import annotations

import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "k8s" / "workload.yaml.tpl"
OUTPUT = ROOT / "artifacts" / "rendered.yaml"
DNS_LABEL = re.compile(r"[a-z0-9](?:[-a-z0-9]*[a-z0-9])?")
LABEL_NAME = r"[A-Za-z0-9](?:[-A-Za-z0-9_.]{0,61}[A-Za-z0-9])?"
IMAGE_DIGEST = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9./:_-]*@sha256:[0-9a-f]{64}"
)


def dns_subdomain(value: str) -> bool:
    return (
        len(value) <= 253
        and all(
            1 <= len(part) <= 63 and DNS_LABEL.fullmatch(part)
            for part in value.split(".")
        )
    )


def label_key(value: str) -> bool:
    if "/" not in value:
        return bool(re.fullmatch(LABEL_NAME, value))
    prefix, name = value.split("/", 1)
    return dns_subdomain(prefix) and bool(re.fullmatch(LABEL_NAME, name))


required = {
    "NAMESPACE": os.environ.get("LAB_NAMESPACE", "open-models-l11"),
    "STORAGE_CLASS": os.environ.get("MODEL_STORAGE_CLASS", ""),
    "NODE_SELECTOR_KEY": os.environ.get("GPU_NODE_SELECTOR_KEY", ""),
    "NODE_SELECTOR_VALUE": os.environ.get("GPU_NODE_SELECTOR_VALUE", ""),
    "IMAGE_URI": os.environ.get("IMAGE_URI", ""),
    "SERIALIZE_GENERATION": os.environ.get("SERIALIZE_GENERATION", "true"),
}

for name, value in required.items():
    if not value:
        raise SystemExit(f"missing required value: {name}")

if not re.fullmatch(
    r"open-models-[a-z0-9](?:[-a-z0-9]*[a-z0-9])?",
    required["NAMESPACE"],
):
    raise SystemExit("LAB_NAMESPACE must start with open-models-")
if len(required["NAMESPACE"]) > 63:
    raise SystemExit("LAB_NAMESPACE must be at most 63 characters")
if not dns_subdomain(required["STORAGE_CLASS"]):
    raise SystemExit("MODEL_STORAGE_CLASS must be a DNS subdomain")
if not label_key(required["NODE_SELECTOR_KEY"]):
    raise SystemExit("GPU_NODE_SELECTOR_KEY is not a valid label key")
if not re.fullmatch(LABEL_NAME, required["NODE_SELECTOR_VALUE"]):
    raise SystemExit("GPU_NODE_SELECTOR_VALUE is not a valid label value")
if not IMAGE_DIGEST.fullmatch(required["IMAGE_URI"]):
    raise SystemExit("IMAGE_URI must be an immutable name@sha256 digest")
if required["SERIALIZE_GENERATION"] not in {"true", "false"}:
    raise SystemExit("SERIALIZE_GENERATION must be true or false")

text = TEMPLATE.read_text(encoding="utf-8")
for name, value in required.items():
    text = text.replace(f"__{name}__", value)
if "__" in text:
    raise SystemExit("unresolved placeholder remains in manifest")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(text, encoding="utf-8")
print(OUTPUT)
