#!/usr/bin/env python3
"""Real PEFT LoRA/QLoRA path layered on the lesson-35 SFT loop concepts."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)


MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def verify_dataset_files(dataset_dir):
    manifest = json.loads((dataset_dir / "manifest.json").read_text())
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise SystemExit("dataset manifest has no files object")
    for split in ("train", "validation", "test"):
        entry = files.get(split)
        path = dataset_dir / f"{split}.jsonl"
        if not isinstance(entry, dict) or not path.is_file():
            raise SystemExit(f"dataset split is absent from manifest: {split}")
        if entry.get("path") != path.name:
            raise SystemExit(f"{split} path differs from dataset manifest")
        if sha256(path) != entry.get("sha256"):
            raise SystemExit(f"{split} sha256 differs from dataset manifest")
        if len(read_rows(path)) != entry.get("rows"):
            raise SystemExit(f"{split} row count differs from dataset manifest")
    return manifest


def encode(tokenizer, source, maximum_length):
    rows = []
    for row in source:
        prompt = tokenizer.apply_chat_template(
            row["messages"][:-1],
            tokenize=True,
            add_generation_prompt=True,
        )
        full = tokenizer.apply_chat_template(
            row["messages"], tokenize=True, add_generation_prompt=False
        )[:maximum_length]
        if full[: len(prompt)] != prompt:
            raise SystemExit(f"{row['id']}: chat template prefix mismatch")
        labels = [-100] * len(prompt) + full[len(prompt) :]
        labels = labels[: len(full)]
        if not any(label != -100 for label in labels):
            raise SystemExit(f"{row['id']}: no supervised tokens")
        rows.append((full, labels))
    return rows


def batch(row, pad):
    return {
        "input_ids": torch.tensor([row[0]], dtype=torch.long),
        "attention_mask": torch.ones((1, len(row[0])), dtype=torch.long),
        "labels": torch.tensor([row[1]], dtype=torch.long),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--method", choices=("lora", "qlora"), required=True)
    parser.add_argument("--rank", type=int, default=8)
    parser.add_argument("--alpha", type=int, default=16)
    parser.add_argument("--targets", default="q_proj,k_proj,v_proj,o_proj")
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--learning-rate", type=float, default=0.0002)
    parser.add_argument("--maximum-length", type=int, default=512)
    args = parser.parse_args()
    targets = [value.strip() for value in args.targets.split(",") if value.strip()]
    if (
        args.rank < 1
        or args.alpha < 1
        or args.steps < 1
        or args.learning_rate <= 0
        or args.maximum_length < 1
        or not targets
        or len(set(targets)) != len(targets)
    ):
        raise SystemExit(
            "rank, alpha, steps, learning rate, maximum length, and unique "
            "target modules must be positive/non-empty"
        )
    verify_dataset_files(args.dataset_dir)
    if not torch.cuda.is_available():
        raise SystemExit("the checked PEFT path requires one CUDA GPU")
    if not torch.cuda.is_bf16_supported():
        raise SystemExit("the checked PEFT path requires BF16-capable CUDA")
    torch.manual_seed(3601)
    quantization = None
    if args.method == "qlora":
        quantization = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        dtype=torch.bfloat16,
        quantization_config=quantization,
        device_map={"": 0},
    )
    model.config.use_cache = False
    if args.method == "qlora":
        model = prepare_model_for_kbit_training(model)
    matched_modules = sorted(
        name
        for name, _ in model.named_modules()
        if any(name == target or name.endswith("." + target) for target in targets)
    )
    missing_targets = [
        target
        for target in targets
        if not any(
            name == target or name.endswith("." + target)
            for name in matched_modules
        )
    ]
    if missing_targets:
        raise SystemExit(
            "target modules not found: " + ", ".join(missing_targets)
        )
    adapter_config = LoraConfig(
        r=args.rank,
        lora_alpha=args.alpha,
        lora_dropout=0.05,
        target_modules=targets,
        task_type="CAUSAL_LM",
        bias="none",
        revision=MODEL_REVISION,
    )
    model = get_peft_model(model, adapter_config)
    model.print_trainable_parameters()
    trainable_parameters = sum(
        parameter.numel()
        for parameter in model.parameters()
        if parameter.requires_grad
    )
    total_parameters = sum(parameter.numel() for parameter in model.parameters())
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID, revision=MODEL_REVISION
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    rows = encode(
        tokenizer,
        read_rows(args.dataset_dir / "train.jsonl"),
        args.maximum_length,
    )
    if not rows:
        raise SystemExit("training split is empty")
    optimizer = torch.optim.AdamW(
        (parameter for parameter in model.parameters() if parameter.requires_grad),
        lr=args.learning_rate,
    )
    model.train()
    args.output.mkdir(parents=True, exist_ok=True)
    effective_config = {
        "schema_version": 1,
        "method": args.method,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "rank": args.rank,
        "alpha": args.alpha,
        "dropout": 0.05,
        "targets": targets,
        "matched_modules": matched_modules,
        "matched_module_count": len(matched_modules),
        "steps": args.steps,
        "learning_rate": args.learning_rate,
        "maximum_length": args.maximum_length,
        "seed": 3601,
        "compute_dtype": "bfloat16",
        "quantization": (
            {
                "storage": "nf4",
                "double_quantization": True,
            }
            if args.method == "qlora"
            else None
        ),
    }
    effective_config_path = args.output / "effective-config.json"
    effective_config_path.write_text(
        json.dumps(effective_config, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "train-log.jsonl").open("w") as log:
        for step in range(1, args.steps + 1):
            current = {
                key: value.cuda()
                for key, value in batch(
                    rows[(step - 1) % len(rows)], tokenizer.pad_token_id
                ).items()
            }
            loss = model(**current).loss
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(
                (p for p in model.parameters() if p.requires_grad), 1.0
            )
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            log.write(
                json.dumps(
                    {
                        "optimizer_step": step,
                        "loss": float(loss.detach().cpu()),
                        "gradient_norm": float(norm.detach().cpu()),
                        "cuda_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                        "cuda_peak_reserved_bytes": torch.cuda.max_memory_reserved(),
                    },
                    sort_keys=True,
                )
                + "\n"
            )
    model.save_pretrained(args.output / "adapter", safe_serialization=True)
    tokenizer.save_pretrained(args.output / "adapter")
    metadata = {
        "schema_version": 1,
        "method": args.method,
        "base_model_id": MODEL_ID,
        "base_model_revision": MODEL_REVISION,
        "dataset_manifest_sha256": sha256(
            args.dataset_dir / "manifest.json"
        ),
        "training_config_sha256": sha256(effective_config_path),
        "rank": args.rank,
        "alpha": args.alpha,
        "targets": targets,
        "matched_modules": matched_modules,
        "matched_module_count": len(matched_modules),
        "steps": args.steps,
        "trainable_parameters": trainable_parameters,
        "total_parameters": total_parameters,
        "trainable_fraction": trainable_parameters / total_parameters,
        "argv": sys.argv,
    }
    (args.output / "provenance.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    (args.output / "adapter" / "training-provenance.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(metadata, sort_keys=True))


if __name__ == "__main__":
    main()
