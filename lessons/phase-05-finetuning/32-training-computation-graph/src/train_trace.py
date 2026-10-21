#!/usr/bin/env python3
"""Train a tiny bigram language model and expose every training-state tensor.

This deliberately uses only the Python standard library. It is small enough to
inspect line by line while preserving the same forward -> loss -> backward ->
optimizer state transition used by larger language-model training systems.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import random
from pathlib import Path


VOCAB = ("<bos>", "red", "green", "blue")
TOKEN_TO_ID = {token: index for index, token in enumerate(VOCAB)}
TRAINING_SEQUENCES = (
    ("<bos>", "red", "green", "blue", "red", "green", "blue"),
    ("<bos>", "green", "blue", "red", "green", "blue", "red"),
    ("<bos>", "blue", "red", "green", "blue", "red", "green"),
)


def pairs() -> list[tuple[int, int]]:
    examples: list[tuple[int, int]] = []
    for sequence in TRAINING_SEQUENCES:
        ids = [TOKEN_TO_ID[token] for token in sequence]
        examples.extend(zip(ids[:-1], ids[1:]))
    return examples


def softmax(logits: list[float]) -> list[float]:
    maximum = max(logits)
    exponentials = [math.exp(value - maximum) for value in logits]
    normalizer = sum(exponentials)
    return [value / normalizer for value in exponentials]


def loss_and_gradient(
    weights: list[list[float]],
    examples: list[tuple[int, int]],
) -> tuple[float, list[list[float]], int]:
    """Return mean cross-entropy, d(loss)/d(weights), and saved activations."""
    vocabulary_size = len(weights)
    gradient = [
        [0.0 for _ in range(vocabulary_size)]
        for _ in range(vocabulary_size)
    ]
    total_loss = 0.0

    for input_id, target_id in examples:
        probabilities = softmax(weights[input_id])
        total_loss -= math.log(max(probabilities[target_id], 1e-12))

        # d cross_entropy / d logits = softmax(logits) - one_hot(target).
        for output_id, probability in enumerate(probabilities):
            gradient[input_id][output_id] += probability
        gradient[input_id][target_id] -= 1.0

    scale = 1.0 / len(examples)
    for row in gradient:
        for index in range(len(row)):
            row[index] *= scale

    # Each example retains the probability vector until its loss is
    # differentiated. A fused implementation may save different intermediates.
    saved_activation_elements = len(examples) * vocabulary_size
    return total_loss * scale, gradient, saved_activation_elements


def global_norm(matrix: list[list[float]]) -> float:
    return math.sqrt(sum(value * value for row in matrix for value in row))


def greedy_generate(
    weights: list[list[float]],
    start: str = "<bos>",
    new_tokens: int = 6,
) -> list[str]:
    current_id = TOKEN_TO_ID[start]
    output = [start]
    for _ in range(new_tokens):
        probabilities = softmax(weights[current_id])
        current_id = max(
            range(len(probabilities)),
            key=lambda index: probabilities[index],
        )
        output.append(VOCAB[current_id])
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--seed", type=int, default=3201)
    parser.add_argument("--learning-rate", type=float, default=0.08)
    parser.add_argument("--clip-norm", type=float, default=1.0)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    args = parser.parse_args()

    if args.steps < 2:
        parser.error("--steps must be at least 2")
    if args.learning_rate <= 0 or args.clip_norm <= 0:
        parser.error("learning rate and clip norm must be positive")

    random_generator = random.Random(args.seed)
    vocabulary_size = len(VOCAB)
    weights = [
        [
            random_generator.uniform(-0.02, 0.02)
            for _ in range(vocabulary_size)
        ]
        for _ in range(vocabulary_size)
    ]
    first_moment = [
        [0.0 for _ in range(vocabulary_size)]
        for _ in range(vocabulary_size)
    ]
    second_moment = [
        [0.0 for _ in range(vocabulary_size)]
        for _ in range(vocabulary_size)
    ]

    training_pairs = pairs()
    beta1 = 0.9
    beta2 = 0.999
    epsilon = 1e-8
    trace = []
    initial_loss = None
    saved_activation_elements = 0

    for step in range(1, args.steps + 1):
        loss, gradient, saved_activation_elements = loss_and_gradient(
            weights,
            training_pairs,
        )
        if initial_loss is None:
            initial_loss = loss

        norm_before_clipping = global_norm(gradient)
        clip_scale = min(1.0, args.clip_norm / max(norm_before_clipping, 1e-12))
        learning_rate = args.learning_rate * min(1.0, step / 10.0)

        for input_id in range(vocabulary_size):
            for output_id in range(vocabulary_size):
                grad = gradient[input_id][output_id] * clip_scale
                first_moment[input_id][output_id] = (
                    beta1 * first_moment[input_id][output_id]
                    + (1.0 - beta1) * grad
                )
                second_moment[input_id][output_id] = (
                    beta2 * second_moment[input_id][output_id]
                    + (1.0 - beta2) * grad * grad
                )
                corrected_first = (
                    first_moment[input_id][output_id]
                    / (1.0 - beta1**step)
                )
                corrected_second = (
                    second_moment[input_id][output_id]
                    / (1.0 - beta2**step)
                )

                # AdamW: decay the parameter independently from the gradient.
                weights[input_id][output_id] *= (
                    1.0 - learning_rate * args.weight_decay
                )
                weights[input_id][output_id] -= learning_rate * (
                    corrected_first
                    / (math.sqrt(corrected_second) + epsilon)
                )

        if step == 1 or step % 10 == 0 or step == args.steps:
            trace.append(
                {
                    "step": step,
                    "loss": loss,
                    "learning_rate": learning_rate,
                    "gradient_norm_before_clip": norm_before_clipping,
                    "clip_scale": clip_scale,
                }
            )

    final_loss, _, _ = loss_and_gradient(weights, training_pairs)
    parameter_elements = vocabulary_size * vocabulary_size
    result = {
        "schema_version": 1,
        "experiment": "tiny-bigram-adamw",
        "seed": args.seed,
        "vocabulary": list(VOCAB),
        "training_pairs": len(training_pairs),
        "initial_loss": initial_loss,
        "final_loss": final_loss,
        "generated_before_claim": (
            "Generation is recorded only after the final update; compare "
            "loss for the controlled learning signal."
        ),
        "generated_after": greedy_generate(weights),
        "steps": trace,
        "graph_inventory": {
            "parameter_elements": parameter_elements,
            "gradient_elements": parameter_elements,
            "optimizer_state_elements": 2 * parameter_elements,
            "saved_activation_elements_per_example": (
                saved_activation_elements // len(training_pairs)
            ),
            "optimizer_state_names": ["adam_first_moment", "adam_second_moment"],
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "initial_loss": initial_loss,
                "final_loss": final_loss,
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
