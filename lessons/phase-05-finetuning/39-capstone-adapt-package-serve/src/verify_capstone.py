#!/usr/bin/env python3
"""Release gate spanning package, frozen evaluation, and oms-benchmark/v1."""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def load(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--base-evaluation", type=Path, required=True)
    parser.add_argument("--tuned-evaluation", type=Path, required=True)
    parser.add_argument("--acceptance", type=Path, required=True)
    parser.add_argument("--evaluation-config", type=Path, required=True)
    parser.add_argument("--base-predictions", type=Path, required=True)
    parser.add_argument("--tuned-predictions", type=Path, required=True)
    parser.add_argument("--tuned-decision", type=Path, required=True)
    parser.add_argument("--evaluation-lock", type=Path, required=True)
    parser.add_argument("--release-gates", type=Path, required=True)
    parser.add_argument("--base-benchmark", type=Path, required=True)
    parser.add_argument("--tuned-benchmark", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("verify_release.py")),
            "--release",
            str(args.release),
        ],
        check=True,
    )
    manifest = load(args.release / "release-manifest.json")
    base_eval = load(args.base_evaluation)
    tuned_eval = load(args.tuned_evaluation)
    decision = load(args.tuned_decision)
    gates = load(args.release_gates)
    base_bench = load(args.base_benchmark)
    tuned_bench = load(args.tuned_benchmark)
    benchmark_validator = (
        Path(__file__).resolve().parents[3]
        / "phase-02-engines"
        / "12-benchmarking-methodology"
        / "bench"
        / "validate_results.py"
    )
    for benchmark in (args.base_benchmark, args.tuned_benchmark):
        subprocess.run(
            [sys.executable, str(benchmark_validator), str(benchmark)],
            check=True,
        )
    if base_eval["contract_name"] != manifest["evaluation_contract"]:
        raise SystemExit("base evaluation uses a different acceptance contract")
    if tuned_eval["contract_name"] != manifest["evaluation_contract"]:
        raise SystemExit("tuned evaluation uses a different acceptance contract")
    evaluation_lock_hash = hashlib.sha256(
        args.evaluation_lock.read_bytes()
    ).hexdigest()
    if evaluation_lock_hash != manifest["evaluation_lock_sha256"]:
        raise SystemExit("evaluation lock hash differs from release provenance")
    evaluation_lock = load(args.evaluation_lock)
    if evaluation_lock["contract_name"] != manifest["evaluation_contract"]:
        raise SystemExit("evaluation lock contract differs from release")
    acceptance_hash = hashlib.sha256(args.acceptance.read_bytes()).hexdigest()
    evaluation_config_hash = hashlib.sha256(
        args.evaluation_config.read_bytes()
    ).hexdigest()
    if acceptance_hash != evaluation_lock["acceptance_sha256"]:
        raise SystemExit("acceptance file differs from the frozen lock")
    if evaluation_config_hash != evaluation_lock["evaluation_config_sha256"]:
        raise SystemExit("evaluation config differs from the frozen lock")
    for label, result in (("base", base_eval), ("tuned", tuned_eval)):
        if result.get("acceptance_sha256") != evaluation_lock[
            "acceptance_sha256"
        ]:
            raise SystemExit(
                f"{label} evaluation acceptance hash differs from lock"
            )
        if result.get("evaluation_config_sha256") != evaluation_lock[
            "evaluation_config_sha256"
        ]:
            raise SystemExit(
                f"{label} evaluation config hash differs from lock"
            )
        if result.get("evaluator_sha256") != evaluation_lock[
            "evaluator_sha256"
        ]:
            raise SystemExit(
                f"{label} evaluator hash differs from lock"
            )
        prediction_hash = result.get("predictions_sha256", "")
        if len(prediction_hash) != 64 or any(
            character not in "0123456789abcdef"
            for character in prediction_hash
        ):
            raise SystemExit(
                f"{label} evaluation has no valid raw-prediction hash"
            )
    evaluation_script = (
        Path(__file__).resolve().parents[2]
        / "34-evaluation-before-optimization"
        / "src"
        / "evaluate.py"
    )
    with tempfile.TemporaryDirectory(prefix="oms-l39-evaluation-") as directory:
        temporary = Path(directory)
        for label, predictions, supplied in (
            ("base", args.base_predictions, base_eval),
            ("tuned", args.tuned_predictions, tuned_eval),
        ):
            output = temporary / f"{label}.json"
            subprocess.run(
                [
                    sys.executable,
                    str(evaluation_script),
                    "--acceptance",
                    str(args.acceptance),
                    "--predictions",
                    str(predictions),
                    "--config",
                    str(args.evaluation_config),
                    "--output",
                    str(output),
                ],
                check=True,
            )
            if load(output) != supplied:
                raise SystemExit(
                    f"{label} evaluation differs from evaluator recomputation"
                )
    release_gates_hash = hashlib.sha256(
        args.release_gates.read_bytes()
    ).hexdigest()
    if release_gates_hash != manifest["release_gates_sha256"]:
        raise SystemExit("release gates hash differs from release provenance")
    if base_eval["examples"] != tuned_eval["examples"]:
        raise SystemExit("base and tuned evaluation counts differ")
    base_ids = {row["id"] for row in base_eval["per_example"]}
    tuned_ids = {row["id"] for row in tuned_eval["per_example"]}
    if base_ids != tuned_ids:
        raise SystemExit("base and tuned evaluation item IDs differ")
    expected_checks = [
        (
            "minimum_overall_pass_rate",
            tuned_eval["overall_pass_rate"],
            gates["minimum_overall_pass_rate"],
        ),
        (
            "maximum_forbidden_hits",
            tuned_eval["forbidden_hits"],
            gates["maximum_forbidden_hits"],
        ),
        (
            "minimum_answered_examples",
            tuned_eval["examples"],
            gates["minimum_answered_examples"],
        ),
    ]
    for name, required in gates["minimum_slice_pass_rate"].items():
        expected_checks.append(
            (
                f"slice:{name}",
                tuned_eval["slices"].get(name, {}).get("pass_rate", 0.0),
                required,
            )
        )
    observed_checks = {
        row["name"]: (row["observed"], row["required"], row["pass"])
        for row in decision["checks"]
    }
    expected_names = {row[0] for row in expected_checks}
    if set(observed_checks) != expected_names:
        raise SystemExit("release decision check names differ from frozen gates")
    for name, observed, required in expected_checks:
        passed = (
            observed <= required
            if name == "maximum_forbidden_hits"
            else observed >= required
        )
        if observed_checks.get(name) != (observed, required, passed):
            raise SystemExit(f"release decision check is inconsistent: {name}")
    expected_release = all(
        observed_checks[name][2] for name in expected_names
    )
    if decision.get("release") is not expected_release:
        raise SystemExit("release decision boolean is inconsistent with checks")
    if decision.get("release") is not True:
        raise SystemExit("tuned artifact did not pass the frozen release gates")
    for result in (base_bench, tuned_bench):
        if result["schema_version"] != "oms-benchmark/v1":
            raise SystemExit("benchmark result does not use oms-benchmark/v1")
        if result["summary"]["success_rate"] != 1.0:
            raise SystemExit("benchmark contains unsuccessful measured requests")
    if base_bench["model"]["artifact"] != "base":
        raise SystemExit("base benchmark is not labeled as the base treatment")
    if tuned_bench["model"]["artifact"] != "tuned":
        raise SystemExit("tuned benchmark is not labeled as the tuned treatment")
    if base_bench["workload"] != tuned_bench["workload"]:
        raise SystemExit("base and tuned benchmark workload contracts differ")
    for key in ("name", "version", "config"):
        if base_bench["engine"][key] != tuned_bench["engine"][key]:
            raise SystemExit(f"serving engine {key} differs between treatments")
    for key in (
        "client_python",
        "client_platform",
        "client_hostname_hash",
        "gpu_name",
        "server_fingerprint",
    ):
        if base_bench["environment"][key] != tuned_bench["environment"][key]:
            raise SystemExit(f"benchmark environment differs: {key}")
    if base_bench["model"]["id"] != manifest["base_model"]["id"]:
        raise SystemExit("base benchmark model ID differs from release base")
    if tuned_bench["model"]["id"] != manifest["served_adapter_name"]:
        raise SystemExit("tuned benchmark model ID differs from adapter alias")
    if manifest["base_model"]["revision"] != base_bench["model"]["revision"]:
        raise SystemExit("benchmark base revision differs from release provenance")
    if manifest["base_model"]["revision"] != tuned_bench["model"]["revision"]:
        raise SystemExit("benchmark tuned base revision differs from release provenance")
    report = {
        "schema_version": 1,
        "release_name": manifest["release_name"],
        "package_verified": True,
        "evaluation_contract": manifest["evaluation_contract"],
        "evaluation_lock_verified": True,
        "release_gate_recomputed": True,
        "base_overall_pass_rate": base_eval["overall_pass_rate"],
        "tuned_overall_pass_rate": tuned_eval["overall_pass_rate"],
        "tuned_release_gate": True,
        "benchmark_contract": "oms-benchmark/v1",
        "benchmark_workload_equal": True,
        "benchmark_environment_equal": True,
        "rollback_inputs_required": [
            "previous immutable Kubernetes manifest",
            "previous release manifest",
            "previous acceptance decision"
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("PASS: package, frozen evaluation, and benchmark evidence agree")


if __name__ == "__main__":
    main()
