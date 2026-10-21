#!/usr/bin/env python3
"""Simulate block prefix caching, chunking, and greedy speculation."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import OrderedDict
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def cache_key(
    previous_hash: str,
    block: list[int],
    model_revision: str,
    tenant: str,
) -> str:
    payload = json.dumps(
        {
            "parent": previous_hash,
            "tokens": block,
            "model_revision": model_revision,
            "tenant": tenant,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def simulate_prefix_cache(config: dict[str, Any]) -> dict[str, Any]:
    block_size = int(config["block_size_tokens"])
    capacity = int(config["cache_capacity_blocks"])
    model_revision = "teaching-model-revision"
    cache: OrderedDict[str, None] = OrderedDict()
    results = []
    for request in config["requests"]:
        parent = "root"
        hits = 0
        inserted = 0
        keys = []
        # Only complete blocks are reusable in this simplified allocator.
        full_length = len(request["tokens"]) // block_size * block_size
        for start in range(0, full_length, block_size):
            block = request["tokens"][start : start + block_size]
            key = cache_key(
                parent, block, model_revision, request["tenant"]
            )
            keys.append(key)
            if key in cache:
                hits += 1
                cache.move_to_end(key)
            else:
                cache[key] = None
                inserted += 1
                while len(cache) > capacity:
                    cache.popitem(last=False)
            parent = key
        results.append(
            {
                "id": request["id"],
                "tenant": request["tenant"],
                "full_blocks": len(keys),
                "hit_blocks": hits,
                "inserted_blocks": inserted,
                "reused_tokens": hits * block_size,
                "uncacheable_tail_tokens": len(request["tokens"]) - full_length,
                "cache_entries_after_request": len(cache),
                "first_key_prefix": keys[0][:12] if keys else None,
            }
        )
    return {
        "block_size_tokens": block_size,
        "capacity_blocks": capacity,
        "key_fields": [
            "parent_block_hash",
            "block_token_ids",
            "model_revision",
            "tenant_isolation",
        ],
        "requests": results,
    }


def simulate_chunking(config: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    for chunk_size in config["chunk_sizes"]:
        long_remaining = int(config["long_prefill_tokens"])
        long_chunk_remaining = 0
        short_prefill = int(config["short_prefill_tokens"])
        short_decode = int(config["short_decode_tokens"])
        arrival = int(config["short_request_arrival_tick"])
        budget_per_tick = int(config["token_budget_per_tick"])
        tick = 0
        short_first_token = None
        timeline = []
        while long_remaining or short_prefill or short_decode:
            budget = budget_per_tick
            work = []
            # A selected prefill chunk is non-preemptible in this structural
            # model. Large chunks therefore occupy several token-budget ticks.
            # Once a chunk boundary is reached, the scheduler prioritizes the
            # waiting short request before selecting the next long chunk.
            if long_chunk_remaining:
                amount = min(long_chunk_remaining, budget)
                long_chunk_remaining -= amount
                long_remaining -= amount
                work.append(f"long-prefill+{amount}")
            elif tick >= arrival and short_prefill:
                amount = min(short_prefill, budget)
                short_prefill -= amount
                budget -= amount
                work.append(f"short-prefill+{amount}")
                if not short_prefill and short_decode and budget:
                    short_decode -= 1
                    short_first_token = (
                        tick if short_first_token is None else short_first_token
                    )
                    work.append("short-decode+1")
            elif tick >= arrival and not short_prefill and short_decode:
                short_decode -= 1
                short_first_token = (
                    tick if short_first_token is None else short_first_token
                )
                work.append("short-decode+1")
            elif long_remaining:
                long_chunk_remaining = min(long_remaining, int(chunk_size))
                amount = min(long_chunk_remaining, budget)
                long_chunk_remaining -= amount
                long_remaining -= amount
                work.append(f"long-prefill+{amount}")
            timeline.append({"tick": tick, "work": work})
            tick += 1
            if tick > 1000:
                raise RuntimeError("chunk simulation did not converge")
        results.append(
            {
                "chunk_size": chunk_size,
                "short_ttft_ticks": short_first_token - arrival,
                "drain_ticks": tick,
                "timeline": timeline,
            }
        )
    return results


def simulate_speculation(case: dict[str, Any]) -> dict[str, Any]:
    target = case["target_tokens"]
    draft = case["draft_tokens"]
    width = int(case["proposal_width"])
    position = 0
    accepted = 0
    proposed = 0
    target_verification_steps = 0
    emitted = []
    rounds = []
    while position < len(target):
        proposal = draft[
            position : position + min(width, len(target) - position)
        ]
        draft_tokens_generated = len(proposal)
        if not proposal:
            proposal = [None]
        target_window = target[position : position + len(proposal)]
        target_verification_steps += 1
        proposed += draft_tokens_generated
        accepted_this_round = 0
        verified_this_round = 0
        mismatch = False
        for proposed_token, target_token in zip(proposal, target_window):
            verified_this_round += 1
            if proposed_token == target_token and not mismatch:
                emitted.append(target_token)
                accepted += 1
                accepted_this_round += 1
                position += 1
            else:
                mismatch = True
                emitted.append(target_token)
                position += 1
                break
        rounds.append(
            {
                "proposal": proposal,
                "target_window": target_window,
                "draft_tokens_generated": draft_tokens_generated,
                "proposal_tokens_checked_through_first_mismatch": (
                    verified_this_round
                ),
                "accepted_prefix_length": accepted_this_round,
                "position_after": position,
            }
        )
    return {
        "name": case["name"],
        "proposal_width": width,
        "proposed_tokens": proposed,
        "accepted_draft_tokens": accepted,
        "acceptance_rate": accepted / proposed if proposed else 0,
        "target_verification_steps": target_verification_steps,
        "ordinary_greedy_target_steps": len(target),
        "emitted_tokens": emitted,
        "target_tokens": target,
        "output_exact_match": emitted == target,
        "rounds": rounds,
        "warning": (
            "step counts omit draft cost, target batch efficiency, sampling "
            "correction, memory, and scheduler contention"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--chunking", type=Path, required=True)
    parser.add_argument("--speculation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {
        "schema_version": "oms-reuse-lookahead/v1",
        "result_kind": (
            "deterministic_mechanism_simulation_not_engine_measurement"
        ),
        "prefix_cache": simulate_prefix_cache(load(args.prefix)),
        "chunked_prefill": simulate_chunking(load(args.chunking)),
        "speculative_decoding": [
            simulate_speculation(case)
            for case in load(args.speculation)["cases"]
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for item in result["prefix_cache"]["requests"]:
        print(
            f"prefix {item['id']:<20} "
            f"hit_blocks={item['hit_blocks']} "
            f"reused_tokens={item['reused_tokens']}"
        )
    for item in result["chunked_prefill"]:
        print(
            f"chunk={item['chunk_size']:<3} "
            f"short_ttft={item['short_ttft_ticks']} ticks"
        )
    for item in result["speculative_decoding"]:
        print(
            f"spec {item['name']:<14} "
            f"acceptance={item['acceptance_rate']:.3f} "
            f"target_steps={item['target_verification_steps']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
