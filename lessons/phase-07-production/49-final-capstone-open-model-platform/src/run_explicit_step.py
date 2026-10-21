#!/usr/bin/env python3
"""Plan or explicitly execute one earlier-lesson script."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ALLOWED_STEPS = {
    "evaluate",
    "render",
    "deploy-private",
    "observe",
    "failure-drill",
    "rollback",
    "teardown",
    "inventory",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--step", choices=sorted(ALLOWED_STEPS), required=True)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--confirm",
        help="With --execute, must equal <project-id>:<step>.",
    )
    parser.add_argument("script_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    contract = json.loads((workspace / "contract.json").read_text(encoding="utf-8"))
    project_id = str(contract["project_id"])
    script = args.script.expanduser().resolve()
    repo_root = Path(__file__).resolve().parents[4]
    lessons_root = repo_root / "lessons"
    try:
        script.relative_to(lessons_root)
    except ValueError as error:
        raise SystemExit("script must be an explicit path under this repository's lessons/") from error
    if not script.is_file():
        raise SystemExit(f"script does not exist: {script}")
    if not script.stat().st_mode & 0o111:
        raise SystemExit(f"script is not executable: {script}")
    forwarded = list(args.script_args)
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]
    command = [str(script), *forwarded]
    cwd = script.parent.parent if script.parent.name == "scripts" else script.parent
    print(f"step={args.step}")
    print(f"cwd={cwd}")
    print("command=" + json.dumps(command))
    if not args.execute:
        print("execution=planned-only")
        print(f"confirmation-required={project_id}:{args.step}")
        return 0
    if args.confirm != f"{project_id}:{args.step}":
        raise SystemExit("typed confirmation does not match project and step")
    if contract.get("validation_mode") != "operator-run":
        raise SystemExit("component execution requires an operator-run workspace")
    print("execution=explicit")
    completed = subprocess.run(command, cwd=cwd, check=False)
    print(f"exit_code={completed.returncode}")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
