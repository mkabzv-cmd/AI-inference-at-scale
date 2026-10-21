#!/usr/bin/env python3
"""An explicit autoregressive generation loop with a KV-cache trace."""

import argparse
import json
import math
import os
import random
import time
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_ID = "sshleifer/tiny-gpt2"
MODEL_REVISION = "5f91d94bd9cd7190a9f3216ff93cd1dd95f2c7be"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--max-new-tokens", type=int, default=12)
    parser.add_argument("--mode", choices=("greedy", "sample"), default="greedy")
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--top-k", type=int, default=0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--compare-high-level", action="store_true")
    parser.add_argument("--inject-cache-bug", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.max_new_tokens < 1:
        parser.error("--max-new-tokens must be at least 1")
    if args.mode == "sample" and args.temperature <= 0:
        parser.error("sampling requires --temperature greater than zero")
    if args.top_k < 0:
        parser.error("--top-k cannot be negative")
    if not 0 < args.top_p <= 1:
        parser.error("--top-p must be in (0, 1]")
    if args.compare_high_level and args.mode != "greedy":
        parser.error("--compare-high-level is intentionally limited to greedy mode")
    return args


def choose_device(requested):
    if requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("--device cuda requested, but torch.cuda.is_available() is false")
    return torch.device(requested)


def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def synchronize(device):
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def apply_top_k_top_p(logits, top_k, top_p):
    filtered = logits.clone()
    if top_k > 0:
        k = min(top_k, filtered.shape[-1])
        threshold = torch.topk(filtered, k).values[..., -1, None]
        filtered = filtered.masked_fill(filtered < threshold, float("-inf"))

    if top_p < 1.0:
        sorted_logits, sorted_indices = torch.sort(filtered, descending=True)
        sorted_probs = torch.softmax(sorted_logits, dim=-1)
        cumulative = torch.cumsum(sorted_probs, dim=-1)
        remove = cumulative > top_p
        remove[..., 1:] = remove[..., :-1].clone()
        remove[..., 0] = False
        scatter_remove = torch.zeros_like(remove).scatter(1, sorted_indices, remove)
        filtered = filtered.masked_fill(scatter_remove, float("-inf"))
    return filtered


def select_token(logits, args):
    if args.mode == "greedy":
        return torch.argmax(logits, dim=-1, keepdim=True), None

    filtered = apply_top_k_top_p(logits / args.temperature, args.top_k, args.top_p)
    probabilities = torch.softmax(filtered, dim=-1)
    token = torch.multinomial(probabilities, num_samples=1)
    selected_probability = probabilities.gather(1, token).item()
    return token, selected_probability


def token_piece(tokenizer, token_id):
    return tokenizer.decode(
        [token_id],
        clean_up_tokenization_spaces=False,
        skip_special_tokens=False,
    )


def main():
    args = parse_args()
    seed_everything(args.seed)
    device = choose_device(args.device)

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        trust_remote_code=False,
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        trust_remote_code=False,
    ).to(device)
    model.eval()
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id

    encoded = tokenizer(args.prompt, return_tensors="pt")
    input_ids = encoded["input_ids"].to(device)
    attention_mask = encoded["attention_mask"].to(device)
    if input_ids.shape[1] == 0:
        raise RuntimeError("prompt produced no tokens")

    prompt_ids = input_ids[0].tolist()
    prompt_pieces = [token_piece(tokenizer, token_id) for token_id in prompt_ids]
    print(f"device: {device}")
    print(f"model: {MODEL_ID} @ {MODEL_REVISION[:8]}...")
    print(f"input_ids: {list(input_ids.shape)}")

    generated_ids = []
    trace = []
    stopped_reason = "max_new_tokens"
    current_input = input_ids
    past_key_values = None
    first_logits_shape = None

    with torch.inference_mode():
        for step_index in range(args.max_new_tokens):
            if past_key_values is not None and args.inject_cache_bug:
                current_input = torch.cat(
                    [input_ids, torch.tensor([generated_ids], device=device)],
                    dim=1,
                )
                raise RuntimeError(
                    "intentional cache-contract failure: past_key_values already "
                    "represent previous tokens, so cached decode must pass only "
                    "new uncached token IDs; received "
                    f"{current_input.shape[1]} token IDs"
                )

            synchronize(device)
            start = time.perf_counter()
            outputs = model(
                input_ids=current_input,
                attention_mask=attention_mask,
                past_key_values=past_key_values,
                use_cache=True,
            )
            synchronize(device)
            forward_ms = (time.perf_counter() - start) * 1000

            if first_logits_shape is None:
                first_logits_shape = list(outputs.logits.shape)
                print(f"logits: {first_logits_shape}")

            next_logits = outputs.logits[:, -1, :]
            next_token, selected_probability = select_token(next_logits, args)
            next_id = int(next_token.item())
            generated_ids.append(next_id)

            phase = "prefill" if step_index == 0 else "decode"
            entry = {
                "step": step_index,
                "phase": phase,
                "model_input_tokens": int(current_input.shape[1]),
                "logits_shape": list(outputs.logits.shape),
                "selected_token_id": next_id,
                "selected_piece": token_piece(tokenizer, next_id),
                "selected_probability": selected_probability,
                "forward_ms": forward_ms,
            }
            trace.append(entry)
            print(
                f"step {step_index:02d} phase={phase:<7} "
                f"input_tokens={current_input.shape[1]} "
                f"selected_id={next_id} forward_ms={forward_ms:.3f}"
            )

            past_key_values = outputs.past_key_values
            if next_id == tokenizer.eos_token_id:
                stopped_reason = "eos_token"
                break

            current_input = next_token
            attention_mask = torch.cat(
                [
                    attention_mask,
                    torch.ones(
                        (attention_mask.shape[0], 1),
                        dtype=attention_mask.dtype,
                        device=device,
                    ),
                ],
                dim=1,
            )

    all_ids = prompt_ids + generated_ids
    generated_text = tokenizer.decode(all_ids, skip_special_tokens=True)
    generated_suffix = tokenizer.decode(generated_ids, skip_special_tokens=True)

    comparison = None
    if args.compare_high_level:
        with torch.inference_mode():
            high_level = model.generate(
                input_ids=input_ids,
                attention_mask=encoded["attention_mask"].to(device),
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        high_level_new = high_level[0, input_ids.shape[1] :].tolist()
        if stopped_reason == "eos_token":
            high_level_new = high_level_new[: len(generated_ids)]
        comparison = {
            "high_level_generated_token_ids": high_level_new,
            "token_ids_match": high_level_new == generated_ids,
        }
        print(f"manual/high-level token IDs match: {comparison['token_ids_match']}")

    result = {
        "schema_version": 1,
        "model": {"id": MODEL_ID, "revision": MODEL_REVISION},
        "software": {
            "torch": torch.__version__,
            "transformers": __import__("transformers").__version__,
        },
        "device": {
            "type": device.type,
            "name": (
                torch.cuda.get_device_name(device)
                if device.type == "cuda"
                else "CPU"
            ),
        },
        "settings": {
            "mode": args.mode,
            "temperature": args.temperature,
            "top_k": args.top_k,
            "top_p": args.top_p,
            "seed": args.seed,
            "max_new_tokens": args.max_new_tokens,
        },
        "prompt": {
            "text": args.prompt,
            "token_ids": prompt_ids,
            "token_pieces": prompt_pieces,
            "token_count": len(prompt_ids),
            "input_ids_shape": list(input_ids.shape),
        },
        "generation": {
            "first_logits_shape": first_logits_shape,
            "generated_token_ids": generated_ids,
            "generated_text": generated_text,
            "generated_suffix": generated_suffix,
            "stopped_reason": stopped_reason,
            "trace": trace,
        },
        "comparison": comparison,
    }

    print(f"generated text: {generated_text!r}")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"result written to {args.output}")
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
