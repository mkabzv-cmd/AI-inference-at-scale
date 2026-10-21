#!/usr/bin/env python3
"""Small dependency-free LoRA forward/backward/merge reference."""

import argparse
import json
from pathlib import Path


def matvec(matrix, vector):
    return [sum(a * b for a, b in zip(row, vector)) for row in matrix]


def add(left, right):
    return [a + b for a, b in zip(left, right)]


def transpose(matrix):
    return [list(column) for column in zip(*matrix)]


def outer(left, right):
    return [[a * b for b in right] for a in left]


def matmul(left, right):
    right_t = transpose(right)
    return [
        [sum(a * b for a, b in zip(row, column)) for column in right_t]
        for row in left
    ]


def matrix_add(left, right):
    return [
        [a + b for a, b in zip(left_row, right_row)]
        for left_row, right_row in zip(left, right)
    ]


def matrix_scale(matrix, scale):
    return [[scale * value for value in row] for row in matrix]


def squared_norm(matrix):
    return sum(value * value for row in matrix for value in row)


def forward(weight, adapter_a, adapter_b, vector, scale):
    base = matvec(weight, vector)
    low_rank = matvec(adapter_b, matvec(adapter_a, vector))
    return add(base, [scale * value for value in low_rank])


def gradients(adapter_a, adapter_b, vector, error, scale):
    projected = matvec(adapter_a, vector)
    gradient_b = matrix_scale(outer(error, projected), scale)
    back_to_rank = matvec(transpose(adapter_b), error)
    gradient_a = matrix_scale(outer(back_to_rank, vector), scale)
    return gradient_a, gradient_b


def update(matrix, gradient, rate):
    return [
        [value - rate * grad for value, grad in zip(row, grad_row)]
        for row, grad_row in zip(matrix, gradient)
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    weight = [[0.4, -0.2, 0.1], [-0.3, 0.5, 0.2]]
    adapter_a = [[0.1, -0.1, 0.2], [-0.2, 0.05, 0.1]]
    adapter_b = [[0.0, 0.0], [0.0, 0.0]]
    vector = [1.0, -2.0, 0.5]
    target = [0.8, -1.2]
    rank = 2
    alpha = 4
    scale = alpha / rank
    rate = 0.1

    before = forward(weight, adapter_a, adapter_b, vector, scale)
    error = [prediction - truth for prediction, truth in zip(before, target)]
    gradient_a_0, gradient_b_0 = gradients(
        adapter_a, adapter_b, vector, error, scale
    )
    adapter_b = update(adapter_b, gradient_b_0, rate)
    after_b_step = forward(weight, adapter_a, adapter_b, vector, scale)
    error_1 = [
        prediction - truth
        for prediction, truth in zip(after_b_step, target)
    ]
    gradient_a_1, gradient_b_1 = gradients(
        adapter_a, adapter_b, vector, error_1, scale
    )
    adapter_a = update(adapter_a, gradient_a_1, rate)
    adapter_b = update(adapter_b, gradient_b_1, rate)
    unmerged = forward(weight, adapter_a, adapter_b, vector, scale)
    merged_weight = matrix_add(
        weight, matrix_scale(matmul(adapter_b, adapter_a), scale)
    )
    merged = matvec(merged_weight, vector)

    report = {
        "schema_version": 1,
        "equation": "y = W x + (alpha / rank) B A x",
        "rank": rank,
        "alpha": alpha,
        "scale": scale,
        "base_weight_unchanged": weight
        == [[0.4, -0.2, 0.1], [-0.3, 0.5, 0.2]],
        "initial_delta_is_zero": before == matvec(weight, vector),
        "initial_gradient_a_squared_norm": squared_norm(gradient_a_0),
        "initial_gradient_b_squared_norm": squared_norm(gradient_b_0),
        "second_gradient_a_squared_norm": squared_norm(gradient_a_1),
        "unmerged_output": unmerged,
        "merged_output": merged,
        "maximum_merge_difference": max(
            abs(a - b) for a, b in zip(unmerged, merged)
        ),
        "trainable_parameter_count": rank * (3 + 2),
        "full_weight_parameter_count": 3 * 2,
    }
    assert report["initial_delta_is_zero"]
    assert report["initial_gradient_a_squared_norm"] == 0.0
    assert report["initial_gradient_b_squared_norm"] > 0.0
    assert report["second_gradient_a_squared_norm"] > 0.0
    assert report["maximum_merge_difference"] < 1e-12
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        "PASS: zero-B initialization, frozen W, adapter gradients, "
        "and merge equivalence verified"
    )


if __name__ == "__main__":
    main()
