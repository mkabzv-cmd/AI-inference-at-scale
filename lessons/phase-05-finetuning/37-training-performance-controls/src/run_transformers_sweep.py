#!/usr/bin/env python3
"""Materialize controlled lesson-35 configs and execute each treatment."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-gpu-run", action="store_true")
    args = parser.parse_args()
    if not args.allow_gpu_run:
        raise SystemExit("pass --allow-gpu-run after recording the budget")
    study = json.loads(args.study.read_text())
    invariants = study["frozen_invariants"]
    manifest_hash = hashlib.sha256(
        (args.dataset_dir / "manifest.json").read_bytes()
    ).hexdigest()
    lesson35 = Path(__file__).resolve().parents[2] / "35-single-gpu-sft"
    base = json.loads((lesson35 / "configs/sft.json").read_text())
    expected_base = {
        "model_id": base["model"]["id"],
        "model_revision": base["model"]["revision"],
        "optimizer": "adamw",
        "learning_rate": base["learning_rate"],
        "weight_decay": base["weight_decay"],
        "maximum_optimizer_steps": base["maximum_optimizer_steps"],
        "maximum_gradient_norm": base["maximum_gradient_norm"],
    }
    mismatches = [
        key
        for key, value in expected_base.items()
        if invariants.get(key) != value
    ]
    if mismatches:
        raise SystemExit(
            "study invariants differ from the executable base config: "
            + ", ".join(mismatches)
        )
    args.output.mkdir(parents=True, exist_ok=True)
    for candidate in study["candidates"]:
        if candidate["layout"] != "padded":
            raise SystemExit(
                "the checked lesson-35 loop implements padded layout only"
            )
        if int(candidate["dataloader_workers"]) != 0:
            raise SystemExit(
                "the checked lesson-35 loop has no DataLoader worker control"
            )
        config = dict(base)
        for key in (
            "microbatch_size",
            "gradient_accumulation_steps",
            "maximum_sequence_length",
            "precision",
            "gradient_checkpointing",
        ):
            source_key = (
                "sequence_length" if key == "maximum_sequence_length" else key
            )
            config[key] = candidate[source_key]
        config["seed"] = int(invariants["seed"])
        config["experiment"] = "lesson-37-" + candidate["name"]
        run_dir = args.output / candidate["name"]
        run_dir.mkdir(parents=True, exist_ok=True)
        config_path = run_dir / "effective-config.json"
        config_path.write_text(
            json.dumps(config, indent=2, sort_keys=True) + "\n"
        )
        subprocess.run(
            [
                sys.executable,
                str(lesson35 / "src/train_transformers.py"),
                "--config",
                str(config_path),
                "--dataset-dir",
                str(args.dataset_dir),
                "--output",
                str(run_dir),
            ],
            check=True,
        )
        provenance = {
            "candidate": candidate,
            "effective_seed": config["seed"],
            "dataset_manifest_sha256": manifest_hash,
            "study_sha256": hashlib.sha256(args.study.read_bytes()).hexdigest(),
            "effective_config_sha256": hashlib.sha256(
                config_path.read_bytes()
            ).hexdigest(),
        }
        (run_dir / "study-provenance.json").write_text(
            json.dumps(provenance, indent=2, sort_keys=True) + "\n"
        )


if __name__ == "__main__":
    main()
