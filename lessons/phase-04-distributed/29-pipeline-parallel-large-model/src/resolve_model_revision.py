#!/usr/bin/env python3
"""Resolve a Hugging Face model HEAD to a recorded immutable revision."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    url = f"https://huggingface.co/api/models/{quote(args.model, safe='/')}"
    request = Request(url, headers={"User-Agent": "oms-learning-roadmap/1"})
    with urlopen(request, timeout=30) as response:
        document = json.load(response)
    revision = document.get("sha")
    if (
        not isinstance(revision, str)
        or len(revision) not in (40, 64)
        or any(character not in "0123456789abcdef" for character in revision)
    ):
        raise SystemExit(f"API returned invalid revision: {revision!r}")
    record = {
        "model_id": args.model,
        "resolved_revision": revision,
        "resolved_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_api": url,
        "license_metadata": document.get("cardData", {}).get("license"),
        "gated": document.get("gated"),
        "private": document.get("private"),
        "warning": (
            "Resolution records current HEAD; inspect the exact revision and "
            "license before use."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"resolved {args.model} -> {revision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
