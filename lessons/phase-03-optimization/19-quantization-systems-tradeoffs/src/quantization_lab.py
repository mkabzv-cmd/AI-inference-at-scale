#!/usr/bin/env python3
"""Dependency-free grouped symmetric weight-quantization experiment."""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any


def l2(values: list[float]) -> float:
    return math.sqrt(sum(value * value for value in values))


def matvec(matrix: list[list[float]], vector: list[float]) -> list[float]:
    return [
        sum(weight * value for weight, value in zip(row, vector))
        for row in matrix
    ]


def quantize_group(values: list[float], bits: int) -> tuple[list[int], float]:
    qmax = 2 ** (bits - 1) - 1
    maximum = max(abs(value) for value in values)
    scale = maximum / qmax if maximum else 1.0
    codes = [
        max(-qmax, min(qmax, round(value / scale)))
        for value in values
    ]
    return codes, scale


def grouped_quantize(
    matrix: list[list[float]], bits: int, group_size: int
) -> tuple[list[list[float]], dict[str, Any]]:
    reconstructed = []
    all_codes: list[int] = []
    all_scales: list[float] = []
    for row in matrix:
        rebuilt_row = []
        for start in range(0, len(row), group_size):
            group = row[start : start + group_size]
            codes, scale = quantize_group(group, bits)
            all_codes.extend(codes)
            all_scales.append(scale)
            rebuilt_row.extend(code * scale for code in codes)
        reconstructed.append(rebuilt_row)

    payload_bits = len(all_codes) * bits
    packed_payload_bytes = math.ceil(payload_bits / 8)
    scale_bytes = len(all_scales) * 4
    return reconstructed, {
        "code_min": min(all_codes),
        "code_max": max(all_codes),
        "scale_count": len(all_scales),
        "ideal_bitpacked_payload_bytes": packed_payload_bytes,
        "fp32_scale_bytes": scale_bytes,
        "estimated_total_bytes": packed_payload_bytes + scale_bytes,
        "first_eight_codes": all_codes[:8],
        "first_scale": all_scales[0],
    }


def make_matrix(
    rows: int, columns: int, rng: random.Random
) -> list[list[float]]:
    matrix = []
    for row_index in range(rows):
        row = [rng.gauss(0, 0.08) for _ in range(columns)]
        # Deterministic outliers make group-size behavior visible.
        row[(row_index * 17) % columns] *= 20
        matrix.append(row)
    return matrix


def evaluate(
    reference: list[list[float]],
    candidate: list[list[float]],
    vectors: list[list[float]],
) -> dict[str, float]:
    weight_errors = [
        candidate[row][column] - reference[row][column]
        for row in range(len(reference))
        for column in range(len(reference[0]))
    ]
    reference_weights = [
        value for row in reference for value in row
    ]
    output_errors = []
    for vector in vectors:
        expected = matvec(reference, vector)
        observed = matvec(candidate, vector)
        difference = [
            actual - target for actual, target in zip(observed, expected)
        ]
        output_errors.append(l2(difference) / max(l2(expected), 1e-12))
    return {
        "weight_rmse": math.sqrt(
            sum(value * value for value in weight_errors) / len(weight_errors)
        ),
        "weight_relative_l2_error": (
            l2(weight_errors) / max(l2(reference_weights), 1e-12)
        ),
        "mean_relative_l2_output_error": (
            sum(output_errors) / len(output_errors)
        ),
        "max_relative_l2_output_error": max(output_errors),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.matrix.read_text(encoding="utf-8"))
    rng = random.Random(int(config["seed"]))
    rows = int(config["rows"])
    columns = int(config["columns"])
    weights = make_matrix(rows, columns, rng)
    vectors = [
        [rng.gauss(0, 1) for _ in range(columns)]
        for _ in range(int(config["evaluation_vectors"]))
    ]
    reference_bytes = rows * columns * 2
    experiments = []
    for experiment in config["experiments"]:
        if experiment["kind"] == "reference":
            storage = {
                "estimated_total_bytes": reference_bytes,
                "note": "idealized FP16 storage; Python objects are much larger",
            }
            metrics = {
                "weight_rmse": 0.0,
                "weight_relative_l2_error": 0.0,
                "mean_relative_l2_output_error": 0.0,
                "max_relative_l2_output_error": 0.0,
            }
        else:
            candidate, storage = grouped_quantize(
                weights,
                int(experiment["bits"]),
                int(experiment["group_size"]),
            )
            metrics = evaluate(weights, candidate, vectors)
        experiments.append(
            {
                **experiment,
                "storage": storage,
                "compression_ratio_vs_fp16": (
                    reference_bytes / storage["estimated_total_bytes"]
                ),
                "numeric_error": metrics,
            }
        )
    result = {
        "schema_version": "oms-toy-quantization/v1",
        "result_kind": "deterministic_toy_numeric_experiment",
        "warning": (
            "No CUDA kernel, tokenizer, or language-model quality is measured"
        ),
        "shape": [rows, columns],
        "reference_storage_bytes": reference_bytes,
        "experiments": experiments,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("experiment             bytes   ratio  mean output error")
    for item in experiments:
        print(
            f"{item['name']:<22}"
            f"{item['storage']['estimated_total_bytes']:>7}"
            f"{item['compression_ratio_vs_fp16']:>8.3f}"
            f"{item['numeric_error']['mean_relative_l2_output_error']:>19.6f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
