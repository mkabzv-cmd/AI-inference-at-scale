#!/usr/bin/env python3
"""Produce an educational prefill/decode timeline in abstract work units."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-tokens", type=int, default=512)
    parser.add_argument("--output-tokens", type=int, default=8)
    parser.add_argument("--layers", type=int, default=24)
    parser.add_argument("--hidden-size", type=int, default=896)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if min(args.prompt_tokens, args.output_tokens, args.layers, args.hidden_size) <= 0:
        parser.error("all numeric values must be positive")

    events = [
        {
            "step": 0,
            "phase": "prefill",
            "new_tokens": args.prompt_tokens,
            "cached_tokens_before": 0,
            "cached_tokens_after": args.prompt_tokens,
            "parallel_token_positions": args.prompt_tokens,
            "attention_score_elements_per_head": (
                args.prompt_tokens * args.prompt_tokens
            ),
        }
    ]
    cached = args.prompt_tokens
    for step in range(1, args.output_tokens + 1):
        events.append(
            {
                "step": step,
                "phase": "decode",
                "new_tokens": 1,
                "cached_tokens_before": cached,
                "cached_tokens_after": cached + 1,
                "parallel_token_positions": 1,
                "attention_score_elements_per_head": cached,
            }
        )
        cached += 1

    result = {
        "schema_version": "oms-prefill-decode-simulation/v1",
        "result_kind": "structural_simulation_not_timing_measurement",
        "tensor_shapes": {
            "prefill_hidden": [
                1,
                args.prompt_tokens,
                args.hidden_size,
            ],
            "decode_hidden_each_step": [1, 1, args.hidden_size],
            "note": "batch dimension is 1 in this simulation",
        },
        "events": events,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("phase  new_tokens  cache_before -> cache_after  score_elements/head")
    for event in events:
        print(
            f"{event['phase']:<7}{event['new_tokens']:>11}"
            f"{event['cached_tokens_before']:>14} ->"
            f"{event['cached_tokens_after']:<12}"
            f"{event['attention_score_elements_per_head']:>10}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
