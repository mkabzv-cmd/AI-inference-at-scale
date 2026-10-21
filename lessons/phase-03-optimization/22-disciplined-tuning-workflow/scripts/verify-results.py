#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


data = json.loads(
    Path(sys.argv[1] if len(sys.argv) > 1 else "artifacts/results.json")
    .read_text(encoding="utf-8")
)
if data["schema_version"] != "oms-tuning-workflow/v1":
    raise SystemExit("unexpected schema")
if not all(item["matched_fixture_answer"] for item in data["diagnoses"]):
    raise SystemExit("one or more pathology diagnoses did not match")
if data["comparison"]["accepted"]:
    raise SystemExit("misleading performance run should be rejected")
reasons = data["comparison"]["rejection_reasons"]
if "quality gate failed" not in reasons or "mean output length changed" not in reasons:
    raise SystemExit("comparison missed confounders")
print("verified three diagnoses and rejection of a confounded speedup")
