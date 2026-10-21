#!/usr/bin/env python3
"""Auditable single-device SFT loop using a pinned Transformers model."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import sys
import time
from pathlib import Path

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def verify_dataset_files(dataset_dir: Path) -> dict:
    """Bind the bytes consumed by training to the checked manifest."""
    manifest_path = dataset_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    declared = manifest.get("files")
    if not isinstance(declared, dict):
        raise SystemExit("dataset manifest has no files object")
    for split in ("train", "validation", "test"):
        entry = declared.get(split)
        if not isinstance(entry, dict):
            raise SystemExit(f"dataset manifest is missing split: {split}")
        path = dataset_dir / f"{split}.jsonl"
        if not path.is_file():
            raise SystemExit(f"dataset split is absent: {path}")
        if entry.get("path") != path.name:
            raise SystemExit(f"{split} path differs from dataset manifest")
        if sha256(path) != entry.get("sha256"):
            raise SystemExit(f"{split} sha256 differs from dataset manifest")
        rows = read_jsonl(path)
        if len(rows) != entry.get("rows"):
            raise SystemExit(f"{split} row count differs from dataset manifest")
    return manifest


def build_rows(tokenizer, source: list[dict], maximum_length: int) -> list[dict]:
    rows = []
    for row in source:
        messages = row["messages"]
        prompt_ids = tokenizer.apply_chat_template(
            messages[:-1],
            tokenize=True,
            add_generation_prompt=True,
        )
        full_ids = tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=False,
        )
        if full_ids[: len(prompt_ids)] != prompt_ids:
            raise ValueError(
                f"{row['id']}: prompt is not a prefix of full chat template"
            )
        input_ids = full_ids[:maximum_length]
        labels = [-100] * min(len(prompt_ids), len(input_ids))
        labels.extend(input_ids[len(labels) :])
        if all(label == -100 for label in labels):
            raise ValueError(
                f"{row['id']}: truncation removed every supervised token"
            )
        rows.append(
            {
                "id": row["id"],
                "input_ids": input_ids,
                "labels": labels,
                "supervised_tokens": sum(label != -100 for label in labels),
            }
        )
    return rows


def collate(rows: list[dict], pad_token_id: int) -> dict:
    maximum = max(len(row["input_ids"]) for row in rows)
    input_ids, attention_mask, labels = [], [], []
    for row in rows:
        padding = maximum - len(row["input_ids"])
        input_ids.append(row["input_ids"] + [pad_token_id] * padding)
        attention_mask.append([1] * len(row["input_ids"]) + [0] * padding)
        labels.append(row["labels"] + [-100] * padding)
    return {
        "input_ids": torch.tensor(input_ids, dtype=torch.long),
        "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
        "labels": torch.tensor(labels, dtype=torch.long),
    }


def scheduler_rate(step: int, maximum: int, warmup: int) -> float:
    if step <= warmup:
        return step / max(1, warmup)
    return max(0.0, (maximum - step) / max(1, maximum - warmup))


@torch.no_grad()
def evaluate(model, rows: list[dict], pad: int, device: torch.device) -> float:
    model.eval()
    losses = []
    for row in rows:
        batch = {
            key: value.to(device) for key, value in collate([row], pad).items()
        }
        losses.append(float(model(**batch).loss.detach().cpu()))
    model.train()
    return sum(losses) / len(losses)


def save_checkpoint(
    output: Path,
    model,
    tokenizer,
    optimizer,
    scheduler,
    state: dict,
) -> Path:
    checkpoint = output / f"checkpoint-{state['optimizer_step']:06d}"
    checkpoint.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(checkpoint, safe_serialization=True)
    tokenizer.save_pretrained(checkpoint)
    torch.save(
        {
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict(),
            "rng_cpu": torch.get_rng_state(),
            "rng_cuda": torch.cuda.get_rng_state_all()
            if torch.cuda.is_available()
            else None,
            "state": state,
        },
        checkpoint / "trainer-state.pt",
    )
    (checkpoint / "run-state.json").write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n"
    )
    return checkpoint


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--stop-after", type=int)
    parser.add_argument("--allow-cpu", action="store_true")
    args = parser.parse_args()

    config = json.loads(args.config.read_text())
    if config.get("precision") not in {"bf16", "fp32"}:
        raise SystemExit("precision must be bf16 or fp32")
    if config.get("assistant_loss_only") is not True:
        raise SystemExit(
            "this checked loop implements assistant_loss_only=true only"
        )
    positive_integer_fields = (
        "maximum_sequence_length",
        "microbatch_size",
        "gradient_accumulation_steps",
        "maximum_optimizer_steps",
        "validation_every_steps",
        "checkpoint_every_steps",
    )
    if any(int(config[field]) < 1 for field in positive_integer_fields):
        raise SystemExit(
            "sequence, batch, step, and interval values must be positive"
        )
    if not 0 <= int(config["warmup_steps"]) <= int(
        config["maximum_optimizer_steps"]
    ):
        raise SystemExit(
            "warmup_steps must be within the optimizer-step budget"
        )
    if (
        float(config["learning_rate"]) <= 0
        or float(config["weight_decay"]) < 0
        or float(config["maximum_gradient_norm"]) <= 0
    ):
        raise SystemExit(
            "optimizer rates and maximum gradient norm are invalid"
        )
    if args.stop_after is not None and args.stop_after < 1:
        raise SystemExit("--stop-after must be positive")
    verify_dataset_files(args.dataset_dir)
    config_hash = sha256(args.config)
    seed = int(config["seed"])
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        device = torch.device("cuda")
    elif args.allow_cpu:
        device = torch.device("cpu")
    else:
        raise SystemExit("CUDA is required unless --allow-cpu is explicit")

    precision = config["precision"]
    if precision == "bf16" and device.type == "cuda":
        if not torch.cuda.is_bf16_supported():
            raise SystemExit("configuration requires bf16-capable CUDA hardware")
        dtype = torch.bfloat16
    else:
        dtype = torch.float32

    model_source = str(args.resume) if args.resume else config["model"]["id"]
    model_kwargs = {"dtype": dtype}
    if not args.resume:
        model_kwargs.update(
            revision=config["model"]["revision"],
            trust_remote_code=config["model"]["trust_remote_code"],
        )
    model = AutoModelForCausalLM.from_pretrained(model_source, **model_kwargs)
    tokenizer = AutoTokenizer.from_pretrained(
        config["model"]["id"],
        revision=config["model"]["tokenizer_revision"],
        trust_remote_code=config["model"]["trust_remote_code"],
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model.config.use_cache = False
    if config["gradient_checkpointing"]:
        model.gradient_checkpointing_enable()
    model.to(device)

    train_source = read_jsonl(args.dataset_dir / "train.jsonl")
    validation_source = read_jsonl(args.dataset_dir / "validation.jsonl")
    if "overfit_examples" in config:
        overfit_examples = int(config["overfit_examples"])
        if overfit_examples < 1:
            raise SystemExit("overfit_examples must be positive")
        train_source = train_source[:overfit_examples]
    if not train_source or not validation_source:
        raise SystemExit(
            "training and validation splits must both be non-empty"
        )
    train_rows = build_rows(
        tokenizer, train_source, int(config["maximum_sequence_length"])
    )
    validation_rows = build_rows(
        tokenizer, validation_source, int(config["maximum_sequence_length"])
    )

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(config["learning_rate"]),
        weight_decay=float(config["weight_decay"]),
    )
    maximum_steps = int(config["maximum_optimizer_steps"])
    warmup_steps = int(config["warmup_steps"])
    scheduler = torch.optim.lr_scheduler.LambdaLR(
        optimizer,
        lambda index: scheduler_rate(
            index + 1, maximum_steps, warmup_steps
        ),
    )
    state = {
        "schema_version": 1,
        "config_sha256": config_hash,
        "dataset_manifest_sha256": sha256(args.dataset_dir / "manifest.json"),
        "optimizer_step": 0,
        "microbatch_cursor": 0,
        "model_id": config["model"]["id"],
        "model_revision": config["model"]["revision"],
        "tokenizer_revision": config["model"]["tokenizer_revision"],
    }
    if args.resume:
        saved = torch.load(
            args.resume / "trainer-state.pt",
            map_location="cpu",
            weights_only=False,
        )
        if saved["state"]["config_sha256"] != config_hash:
            raise SystemExit("checkpoint configuration mismatch")
        if saved["state"]["dataset_manifest_sha256"] != state[
            "dataset_manifest_sha256"
        ]:
            raise SystemExit("checkpoint dataset manifest mismatch")
        optimizer.load_state_dict(saved["optimizer"])
        scheduler.load_state_dict(saved["scheduler"])
        torch.set_rng_state(saved["rng_cpu"])
        if device.type == "cuda" and saved["rng_cuda"] is not None:
            torch.cuda.set_rng_state_all(saved["rng_cuda"])
        state = saved["state"]

    args.output.mkdir(parents=True, exist_ok=True)
    effective_config = args.output / "effective-config.json"
    if effective_config.exists() and sha256(effective_config) != config_hash:
        raise SystemExit("output directory already contains a different config")
    effective_config.write_bytes(args.config.read_bytes())
    environment = {
        "schema_version": 1,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "cuda_runtime": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version()
        if torch.backends.cudnn.is_available()
        else None,
        "device": str(device),
        "gpu_name": torch.cuda.get_device_name(device)
        if device.type == "cuda"
        else None,
        "gpu_capability": list(torch.cuda.get_device_capability(device))
        if device.type == "cuda"
        else None,
    }
    (args.output / "environment.json").write_text(
        json.dumps(environment, indent=2, sort_keys=True) + "\n"
    )
    log_path = args.output / "train-log.jsonl"
    log_mode = "a" if args.resume else "w"
    accumulation = int(config["gradient_accumulation_steps"])
    microbatch = int(config["microbatch_size"])
    maximum_norm = float(config["maximum_gradient_norm"])
    optimizer.zero_grad(set_to_none=True)
    model.train()

    with log_path.open(log_mode) as log:
        while state["optimizer_step"] < maximum_steps:
            step_started = time.perf_counter()
            accumulated_loss = 0.0
            supervised_tokens = 0
            for _ in range(accumulation):
                selected = []
                for _ in range(microbatch):
                    selected.append(
                        train_rows[
                            state["microbatch_cursor"] % len(train_rows)
                        ]
                    )
                    state["microbatch_cursor"] += 1
                supervised_tokens += sum(
                    row["supervised_tokens"] for row in selected
                )
                batch = {
                    key: value.to(device)
                    for key, value in collate(
                        selected, tokenizer.pad_token_id
                    ).items()
                }
                autocast_enabled = device.type == "cuda" and dtype != torch.float32
                with torch.autocast(
                    device_type=device.type,
                    dtype=dtype if autocast_enabled else None,
                    enabled=autocast_enabled,
                ):
                    loss = model(**batch).loss / accumulation
                loss.backward()
                accumulated_loss += float(loss.detach().cpu())

            raw_norm = torch.nn.utils.clip_grad_norm_(
                model.parameters(), maximum_norm
            )
            current_learning_rate = optimizer.param_groups[0]["lr"]
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad(set_to_none=True)
            state["optimizer_step"] += 1
            step = state["optimizer_step"]
            record = {
                "schema_version": 1,
                "optimizer_step": step,
                "microbatches_consumed": state["microbatch_cursor"],
                "train_loss": accumulated_loss,
                "gradient_norm_before_clip": float(raw_norm.detach().cpu()),
                "learning_rate": current_learning_rate,
                "supervised_tokens": supervised_tokens,
                "step_seconds": time.perf_counter() - step_started,
                "cuda_peak_allocated_bytes": torch.cuda.max_memory_allocated()
                if device.type == "cuda"
                else 0,
                "cuda_peak_reserved_bytes": torch.cuda.max_memory_reserved()
                if device.type == "cuda"
                else 0,
            }
            if step % int(config["validation_every_steps"]) == 0:
                record["validation_loss"] = evaluate(
                    model, validation_rows, tokenizer.pad_token_id, device
                )
            log.write(json.dumps(record, sort_keys=True) + "\n")
            log.flush()
            if step % int(config["checkpoint_every_steps"]) == 0:
                save_checkpoint(
                    args.output,
                    model,
                    tokenizer,
                    optimizer,
                    scheduler,
                    state,
                )
            if args.stop_after is not None and step >= args.stop_after:
                save_checkpoint(
                    args.output,
                    model,
                    tokenizer,
                    optimizer,
                    scheduler,
                    state,
                )
                break

    final_validation_loss = evaluate(
        model, validation_rows, tokenizer.pad_token_id, device
    )
    complete = state["optimizer_step"] == maximum_steps
    summary = {
        **state,
        "complete": complete,
        "final_validation_loss": final_validation_loss,
        "train_examples": len(train_rows),
        "validation_examples": len(validation_rows),
        "device": str(device),
        "dtype": str(dtype),
        "finite": math.isfinite(final_validation_loss),
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
