#!/usr/bin/env python3
"""Prove the study verifier rejects a silently changed workload."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path


source_root = Path("artifacts/raw")
files = sorted(source_root.glob("*/*.json"))
if not files:
    raise SystemExit("capture at least one engine first")
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    for path in files:
        destination = root / path.relative_to(source_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    victim = next(root.glob("*/*.json"))
    data = json.loads(victim.read_text())
    data["workload"]["temperature"] = 0.7
    victim.write_text(json.dumps(data, indent=2) + "\n")
    result = subprocess.run(
        [
            "python3",
            "scripts/verify_study.py",
            str(root),
            "--allow-incomplete",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        raise SystemExit("verifier accepted a contaminated workload")
    Path("artifacts/failure-verifier.txt").write_text(
        result.stdout + result.stderr
    )
    print("verifier rejected the changed sampling configuration")
