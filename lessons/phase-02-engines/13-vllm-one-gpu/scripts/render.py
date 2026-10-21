#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from pathlib import Path


root = Path(__file__).resolve().parent.parent
dns_label = re.compile(r"[a-z0-9](?:[-a-z0-9]*[a-z0-9])?")
label_name = r"[A-Za-z0-9](?:[-A-Za-z0-9_.]{0,61}[A-Za-z0-9])?"
image_digest = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9./:_-]*@sha256:[0-9a-f]{64}"
)


def valid_dns_subdomain(value: str) -> bool:
    return (
        len(value) <= 253
        and all(
            1 <= len(part) <= 63 and dns_label.fullmatch(part)
            for part in value.split(".")
        )
    )


def valid_label_key(value: str) -> bool:
    if "/" not in value:
        return bool(re.fullmatch(label_name, value))
    prefix, name = value.split("/", 1)
    return valid_dns_subdomain(prefix) and bool(
        re.fullmatch(label_name, name)
    )


values = {
    "NAMESPACE": os.environ.get("LAB_NAMESPACE", "open-models-l13"),
    "STORAGE_CLASS": os.environ.get("MODEL_STORAGE_CLASS", ""),
    "NODE_SELECTOR_KEY": os.environ.get("GPU_NODE_SELECTOR_KEY", ""),
    "NODE_SELECTOR_VALUE": os.environ.get("GPU_NODE_SELECTOR_VALUE", ""),
    "IMAGE_URI": os.environ.get("IMAGE_URI", ""),
    "GPU_MEMORY_UTILIZATION": os.environ.get("GPU_MEMORY_UTILIZATION", "0.80"),
    "MAX_NUM_SEQS": os.environ.get("MAX_NUM_SEQS", "16"),
}
for key, value in values.items():
    if not value:
        raise SystemExit(f"missing {key}")
if not re.fullmatch(
    r"open-models-[a-z0-9](?:[-a-z0-9]*[a-z0-9])?",
    values["NAMESPACE"],
):
    raise SystemExit("unsafe namespace")
if len(values["NAMESPACE"]) > 63:
    raise SystemExit("LAB_NAMESPACE must be at most 63 characters")
if not valid_dns_subdomain(values["STORAGE_CLASS"]):
    raise SystemExit("MODEL_STORAGE_CLASS must be a DNS subdomain")
if not valid_label_key(values["NODE_SELECTOR_KEY"]):
    raise SystemExit("GPU_NODE_SELECTOR_KEY is not a valid label key")
if not re.fullmatch(label_name, values["NODE_SELECTOR_VALUE"]):
    raise SystemExit("GPU_NODE_SELECTOR_VALUE is not a valid label value")
if not image_digest.fullmatch(values["IMAGE_URI"]):
    raise SystemExit("IMAGE_URI must be an immutable name@sha256 digest")
utilization = float(values["GPU_MEMORY_UTILIZATION"])
if not 0.1 <= utilization <= 0.95:
    raise SystemExit("GPU_MEMORY_UTILIZATION safety range is 0.10..0.95")
if not 1 <= int(values["MAX_NUM_SEQS"]) <= 64:
    raise SystemExit("MAX_NUM_SEQS safety range is 1..64")

rendered = (root / "k8s/workload.yaml.tpl").read_text()
for key, value in values.items():
    rendered = rendered.replace(f"__{key}__", value)
if "__" in rendered:
    raise SystemExit("unresolved template placeholder")
(root / "artifacts").mkdir(exist_ok=True)
(root / "artifacts/rendered.yaml").write_text(rendered)
print(root / "artifacts/rendered.yaml")
