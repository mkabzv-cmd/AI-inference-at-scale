#!/usr/bin/env python3
"""Render narrowly defined placeholders without requiring envsubst."""

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / ".lab"

values = {
    "__NAMESPACE__": os.environ.get("LAB_NAMESPACE", ""),
    "__NODEGROUP__": os.environ.get("GPU_NODEGROUP_NAME", ""),
    "__IMAGE_URI_WITH_DIGEST__": os.environ.get("IMAGE_URI_WITH_DIGEST", ""),
}
for placeholder, value in values.items():
    if not value:
        raise SystemExit(f"missing environment value for {placeholder}")

dns_label = re.compile(r"^open-models-[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
if len(values["__NAMESPACE__"]) > 63 or not dns_label.fullmatch(
    values["__NAMESPACE__"]
):
    raise SystemExit(
        "LAB_NAMESPACE must be a DNS label beginning with open-models-"
    )
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,62}", values["__NODEGROUP__"]):
    raise SystemExit("GPU_NODEGROUP_NAME contains unsupported characters")
ecr_digest_uri = re.compile(
    r"[0-9]{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com(?:\.cn)?/"
    r"[a-z0-9][a-z0-9._/-]*@sha256:[0-9a-f]{64}"
)
if not ecr_digest_uri.fullmatch(values["__IMAGE_URI_WITH_DIGEST__"]):
    raise SystemExit("IMAGE_URI_WITH_DIGEST must be a complete private ECR digest URI")

OUTPUT.mkdir(parents=True, exist_ok=True)
for input_name, output_name in (
    ("workload.yaml.tpl", "workload.yaml"),
    ("failure-two-gpus.yaml.tpl", "failure-two-gpus.yaml"),
):
    rendered = (ROOT / "k8s" / input_name).read_text(encoding="utf-8")
    for placeholder, value in values.items():
        rendered = rendered.replace(placeholder, value)
    leftovers = re.findall(r"__[A-Z0-9_]+__", rendered)
    if leftovers:
        raise SystemExit(f"unrendered placeholders in {input_name}: {leftovers}")
    (OUTPUT / output_name).write_text(rendered, encoding="utf-8")
    print(f"rendered {OUTPUT / output_name}")
