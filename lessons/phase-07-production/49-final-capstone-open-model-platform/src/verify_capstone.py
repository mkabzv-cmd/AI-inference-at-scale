#!/usr/bin/env python3
"""Fail-closed verifier for the lesson-49 capstone evidence workspace."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import tempfile
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
IMAGE_DIGEST = re.compile(r"^[A-Za-z0-9._/:-]+@sha256:[0-9a-f]{64}$")
PROJECT_ID = re.compile(r"^[a-z][a-z0-9-]{2,62}$")
NAMESPACE = re.compile(r"^[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?$")
RELEASE_ID = re.compile(r"^[A-Za-z0-9](?:[-A-Za-z0-9._]{1,61}[A-Za-z0-9])$")
UNRESOLVED = re.compile(
    r"(__[A-Z][A-Z0-9_]+__|\bTO" r"DO\b|\bT" r"BD\b|\bFIX" r"ME\b|\bCHANGE" r"ME\b|"
    r"<\s*replace(?:[-_ ]me)?\s*>)",
    re.IGNORECASE,
)
SECRET_PATTERNS = {
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\b(?:github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{30,})\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}
REQUIRED_GATES = {
    "quality",
    "performance",
    "security",
    "reliability",
    "cost",
    "cleanup",
}


@dataclass(frozen=True)
class Violation:
    code: str
    path: str
    message: str


class VirtualWorkspace:
    """Read a workspace once, then optionally apply a teaching-only overlay."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.files: dict[str, bytes] = {}
        self.symlinks: list[str] = []
        if not self.root.is_dir():
            raise ValueError(f"workspace is not a directory: {self.root}")
        for path in sorted(self.root.rglob("*")):
            rel = path.relative_to(self.root).as_posix()
            if path.is_symlink():
                self.symlinks.append(rel)
            elif path.is_file():
                self.files[rel] = path.read_bytes()

    def apply_overlay(self, overlay_path: Path) -> dict[str, Any]:
        overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
        if overlay.get("schema_version") != 1:
            raise ValueError("overlay schema_version must be 1")
        for operation in overlay.get("operations", []):
            op = operation.get("op")
            rel = safe_relative(str(operation.get("path", "")))
            if op == "delete_file":
                self.files.pop(rel, None)
            elif op == "set_json":
                if rel not in self.files:
                    raise ValueError(f"overlay target does not exist: {rel}")
                value = json.loads(self.files[rel].decode("utf-8"))
                set_json_pointer(value, str(operation["pointer"]), operation.get("value"))
                self.files[rel] = (
                    json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"
                )
            elif op == "replace_text":
                if rel not in self.files:
                    raise ValueError(f"overlay target does not exist: {rel}")
                old = str(operation["old"])
                new = str(operation["new"])
                text = self.files[rel].decode("utf-8")
                if old not in text:
                    raise ValueError(f"overlay text not found in {rel}: {old!r}")
                self.files[rel] = text.replace(old, new).encode("utf-8")
            else:
                raise ValueError(f"unsupported overlay operation: {op!r}")
        return overlay

    def exists(self, rel: str) -> bool:
        return rel in self.files

    def bytes(self, rel: str) -> bytes:
        return self.files[rel]

    def text(self, rel: str) -> str:
        return self.bytes(rel).decode("utf-8")

    def json(self, rel: str) -> Any:
        return json.loads(self.text(rel))

    def sha256(self, rel: str) -> str:
        return hashlib.sha256(self.bytes(rel)).hexdigest()


def safe_relative(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or path.is_absolute()
        or ".." in path.parts
        or path.as_posix() != value
    ):
        raise ValueError(f"path must be a normalized relative path: {value!r}")
    return path.as_posix()


def set_json_pointer(document: Any, pointer: str, value: Any) -> None:
    if not pointer.startswith("/"):
        raise ValueError(f"JSON pointer must start with '/': {pointer!r}")
    parts = [
        token.replace("~1", "/").replace("~0", "~")
        for token in pointer.lstrip("/").split("/")
    ]
    current = document
    for token in parts[:-1]:
        current = current[int(token)] if isinstance(current, list) else current[token]
    final = parts[-1]
    if isinstance(current, list):
        current[int(final)] = value
    else:
        current[final] = value


def parse_time(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


class Verifier:
    def __init__(self, workspace: VirtualWorkspace, require_operator_run: bool) -> None:
        self.workspace = workspace
        self.require_operator_run = require_operator_run
        self.violations: list[Violation] = []
        self.contract: dict[str, Any] = {}
        self.release: dict[str, Any] = {}
        self.environment: dict[str, Any] = {}
        self.validation_mode = "unknown"

    def fail(self, code: str, path: str, message: str) -> None:
        self.violations.append(Violation(code, path, message))

    def load_json(self, rel: str, required: bool = True) -> dict[str, Any] | None:
        try:
            rel = safe_relative(rel)
        except ValueError as error:
            self.fail("UNSAFE_PATH", rel, str(error))
            return None
        if not self.workspace.exists(rel):
            if required:
                self.fail("FILE_MISSING", rel, "required file is missing")
            return None
        try:
            value = self.workspace.json(rel)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            self.fail("INVALID_JSON", rel, str(error))
            return None
        if not isinstance(value, dict):
            self.fail("INVALID_JSON_SHAPE", rel, "top-level JSON value must be an object")
            return None
        return value

    def run(self) -> None:
        for rel in self.workspace.symlinks:
            self.fail("SYMLINK_FORBIDDEN", rel, "capstone evidence cannot be a symlink")

        contract = self.load_json("contract.json")
        if contract is None:
            return
        self.contract = contract
        self.validate_contract()
        self.validate_inventory_and_index()

        paths = contract.get("paths", {})
        if not isinstance(paths, dict):
            self.fail("CONTRACT_PATHS", "contract.json", "paths must be an object")
            return
        release_path = str(paths.get("release", "release.json"))
        environment_path = str(paths.get("environment", "environment.json"))
        release = self.load_json(release_path)
        environment = self.load_json(environment_path)
        if release is None or environment is None:
            return
        self.release = release
        self.environment = environment

        self.validate_release_identity(release_path, environment_path)
        self.validate_artifacts()
        self.validate_topology()
        self.validate_gates()
        self.validate_promotion()
        self.validate_kubernetes(str(paths.get("kubernetes_manifest", "")))
        self.scan_content()

    def validate_contract(self) -> None:
        contract = self.contract
        if contract.get("schema_version") != 1:
            self.fail("CONTRACT_SCHEMA", "contract.json", "schema_version must be 1")
        project_id = str(contract.get("project_id", ""))
        if not PROJECT_ID.fullmatch(project_id):
            self.fail("PROJECT_ID", "contract.json", "project_id must be lowercase DNS-like text")
        mode = str(contract.get("validation_mode", ""))
        self.validation_mode = mode
        if mode not in {"fixture", "operator-run"}:
            self.fail("VALIDATION_MODE", "contract.json", "validation_mode is not recognized")
        if self.require_operator_run and mode != "operator-run":
            self.fail(
                "OPERATOR_RUN_REQUIRED",
                "contract.json",
                "fixture evidence cannot qualify a live capstone release",
            )
        claim_scope = str(contract.get("claim_scope", ""))
        if mode == "fixture" and claim_scope != "verifier-exercise-only":
            self.fail(
                "FIXTURE_SCOPE",
                "contract.json",
                "fixture claim_scope must be verifier-exercise-only",
            )
        if mode == "operator-run" and len(claim_scope.strip()) < 12:
            self.fail(
                "CLAIM_SCOPE",
                "contract.json",
                "operator-run claim_scope must state a meaningful boundary",
            )
        topology = contract.get("serving_topology")
        if topology not in {"one-gpu", "three-node"}:
            self.fail("TOPOLOGY", "contract.json", "topology must be one-gpu or three-node")
        model = contract.get("model", {})
        if not isinstance(model, dict):
            self.fail("MODEL_CONTRACT", "contract.json", "model must be an object")
            return
        if not str(model.get("id", "")).strip():
            self.fail("MODEL_ID", "contract.json", "model id is required")
        revision = str(model.get("revision", ""))
        tokenizer = str(model.get("tokenizer_revision", ""))
        if not HEX40.fullmatch(revision):
            self.fail("MODEL_REVISION", "contract.json", "model revision must be 40 lowercase hex")
        if tokenizer != revision:
            self.fail(
                "TOKENIZER_REVISION_MISMATCH",
                "contract.json",
                "tokenizer revision must equal the selected model revision",
            )
        features = contract.get("features")
        if not isinstance(features, dict):
            self.fail("FEATURES", "contract.json", "features must be an object")
        else:
            for name in ("adapter", "rag"):
                if not isinstance(features.get(name), bool):
                    self.fail(
                        "FEATURES",
                        "contract.json",
                        f"features.{name} must be boolean",
                    )

    def validate_inventory_and_index(self) -> None:
        required_raw = self.contract.get("required_files")
        if not isinstance(required_raw, list) or not required_raw:
            self.fail("REQUIRED_FILES", "contract.json", "required_files must be a non-empty list")
            return
        required: list[str] = []
        for value in required_raw:
            try:
                required.append(safe_relative(str(value)))
            except ValueError as error:
                self.fail("UNSAFE_PATH", "contract.json", str(error))
        if len(required) != len(set(required)):
            self.fail("DUPLICATE_REQUIRED_FILE", "contract.json", "required_files contains duplicates")

        index_path = str(self.contract.get("paths", {}).get("evidence_index", ""))
        index = self.load_json(index_path)
        if index is None:
            return
        if index.get("schema_version") != 1:
            self.fail("INDEX_SCHEMA", index_path, "schema_version must be 1")
        for key in ("project_id", "release_id"):
            if index.get(key) != self.contract.get(key):
                self.fail("INDEX_ID_MISMATCH", index_path, f"{key} differs from contract")
        entries = index.get("entries")
        if not isinstance(entries, list):
            self.fail("INDEX_ENTRIES", index_path, "entries must be an array")
            return
        indexed: dict[str, str] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                self.fail("INDEX_ENTRY", index_path, "each entry must be an object")
                continue
            try:
                rel = safe_relative(str(entry.get("path", "")))
            except ValueError as error:
                self.fail("UNSAFE_PATH", index_path, str(error))
                continue
            digest = str(entry.get("sha256", ""))
            if rel in indexed:
                self.fail("DUPLICATE_INDEX_ENTRY", index_path, f"duplicate entry for {rel}")
            indexed[rel] = digest
            if not HEX64.fullmatch(digest):
                self.fail("INDEX_DIGEST", index_path, f"invalid SHA-256 for {rel}")
            if not self.workspace.exists(rel):
                self.fail("INDEXED_FILE_MISSING", rel, "file named by evidence index is missing")
            elif self.workspace.sha256(rel) != digest:
                self.fail("HASH_MISMATCH", rel, "bytes do not match evidence-index SHA-256")

        if set(indexed) != set(required):
            missing = sorted(set(required) - set(indexed))
            extra = sorted(set(indexed) - set(required))
            self.fail(
                "INDEX_SET_MISMATCH",
                index_path,
                f"index/contract differ; missing={missing}, extra={extra}",
            )
        actual = set(self.workspace.files) - {index_path}
        if actual != set(required):
            missing = sorted(set(required) - actual)
            undeclared = sorted(actual - set(required))
            self.fail(
                "WORKSPACE_FILE_SET",
                ".",
                f"workspace must be exact; missing={missing}, undeclared={undeclared}",
            )

    def validate_release_identity(self, release_path: str, environment_path: str) -> None:
        release = self.release
        environment = self.environment
        contract = self.contract
        for key in ("project_id", "environment_id", "release_id"):
            wanted = contract.get(key)
            if release.get(key) != wanted:
                self.fail("RELEASE_ID_MISMATCH", release_path, f"{key} differs from contract")
            if environment.get(key) != wanted:
                self.fail("ENVIRONMENT_ID_MISMATCH", environment_path, f"{key} differs from contract")
        if release.get("schema_version") != 1 or environment.get("schema_version") != 1:
            self.fail("DOCUMENT_SCHEMA", ".", "release and environment schema_version must be 1")
        if environment.get("validation_mode") != self.validation_mode:
            self.fail(
                "ENVIRONMENT_MODE_MISMATCH",
                environment_path,
                "environment validation_mode differs from contract",
            )
        if environment.get("network_exposure") != "private":
            self.fail(
                "PUBLIC_EXPOSURE",
                environment_path,
                "network_exposure must remain private",
            )
        if environment.get("service_type") != "ClusterIP":
            self.fail("PUBLIC_EXPOSURE", environment_path, "service_type must be ClusterIP")
        if not NAMESPACE.fullmatch(str(environment.get("namespace", ""))):
            self.fail(
                "ENVIRONMENT_NAMESPACE",
                environment_path,
                "namespace must be a Kubernetes DNS label",
            )
        for field in ("cluster_context", "region", "operator"):
            if len(str(environment.get(field, "")).strip()) < 3:
                self.fail(
                    "ENVIRONMENT_METADATA",
                    environment_path,
                    f"{field} must identify the observed environment",
                )
        if not parse_time(environment.get("captured_at")):
            self.fail(
                "ENVIRONMENT_TIME",
                environment_path,
                "captured_at must be an ISO-8601 timestamp with a timezone",
            )
        if not RELEASE_ID.fullmatch(str(contract.get("release_id", ""))):
            self.fail(
                "RELEASE_ID",
                "contract.json",
                "release_id must be safe for a Kubernetes label value",
            )

        source_revision = str(release.get("source_revision", ""))
        if not HEX40.fullmatch(source_revision):
            self.fail("SOURCE_REVISION", release_path, "source revision must be 40 lowercase hex")
        image = str(release.get("image", ""))
        if not IMAGE_DIGEST.fullmatch(image):
            self.fail("MUTABLE_IMAGE", release_path, "image must use an exact sha256 digest")
        for owner_path, owner in ((release_path, release), (environment_path, environment)):
            model = owner.get("model", {})
            if not isinstance(model, dict) or model != contract.get("model"):
                self.fail("MODEL_IDENTITY_MISMATCH", owner_path, "model identity differs from contract")

    def validate_artifacts(self) -> None:
        release = self.release
        features = self.contract.get("features", {})
        if not isinstance(features, dict):
            features = {}
        serving = release.get("serving", {})
        evaluation = release.get("evaluation", {})
        adapter = release.get("adapter", {})
        rag = release.get("rag", {})
        if not all(isinstance(value, dict) for value in (serving, evaluation, adapter, rag)):
            self.fail("RELEASE_ARTIFACT_SHAPE", "release.json", "artifact sections must be objects")
            return
        self.check_bound_hash(
            str(serving.get("configuration_path", "")),
            str(serving.get("configuration_sha256", "")),
            "SERVING_CONFIG",
        )
        self.check_bound_hash(
            str(evaluation.get("dataset_path", "")),
            str(evaluation.get("dataset_sha256", "")),
            "EVAL_DATASET",
        )
        self.check_bound_hash(
            str(adapter.get("path", "")),
            str(adapter.get("sha256", "")),
            "ADAPTER_ARTIFACT",
        )
        self.check_bound_hash(
            str(rag.get("path", "")),
            str(rag.get("sha256", "")),
            "RAG_ARTIFACT",
        )
        adapter_enabled = adapter.get("enabled")
        rag_enabled = rag.get("enabled")
        if not isinstance(adapter_enabled, bool):
            self.fail("ADAPTER_FEATURE_MISMATCH", "release.json", "adapter enabled must be boolean")
        if not isinstance(rag_enabled, bool):
            self.fail("RAG_FEATURE_MISMATCH", "release.json", "RAG enabled must be boolean")
        if adapter_enabled != features.get("adapter"):
            self.fail("ADAPTER_FEATURE_MISMATCH", "release.json", "adapter enablement differs")
        if rag_enabled != features.get("rag"):
            self.fail("RAG_FEATURE_MISMATCH", "release.json", "RAG enablement differs")
        model_revision = self.contract.get("model", {}).get("revision")
        if adapter.get("base_model_revision") != model_revision:
            self.fail(
                "ADAPTER_BASE_MISMATCH",
                "release.json",
                "adapter base revision differs from selected model",
            )
        if adapter_enabled is True and adapter.get("format") != "safetensors":
            self.fail("ADAPTER_FORMAT", "release.json", "enabled adapter must use safetensors")
        if rag_enabled is True:
            for key in ("corpus_version", "index_version"):
                if str(rag.get(key, "")).lower() in {"", "latest", "main"}:
                    self.fail("MUTABLE_RAG_VERSION", "release.json", f"{key} must be immutable")

        serving_path = str(serving.get("configuration_path", ""))
        serving_record = self.load_json(serving_path)
        if serving_record is not None:
            for field in ("engine", "engine_version"):
                if serving_record.get(field) != serving.get(field):
                    self.fail(
                        "SERVING_CONFIG_MISMATCH",
                        serving_path,
                        f"{field} differs from release",
                    )
            for field in ("max_model_length", "max_concurrent_requests"):
                value = serving_record.get(field)
                if type(value) is not int or value < 1:
                    self.fail(
                        "SERVING_CONFIG",
                        serving_path,
                        f"{field} must be a positive integer",
                    )
            utilization = serving_record.get("gpu_memory_utilization")
            if (
                not isinstance(utilization, (int, float))
                or isinstance(utilization, bool)
                or not math.isfinite(float(utilization))
                or not 0 < float(utilization) < 1
            ):
                self.fail(
                    "SERVING_CONFIG",
                    serving_path,
                    "gpu_memory_utilization must be finite and between zero and one",
                )

        evaluation_path = str(evaluation.get("dataset_path", ""))
        evaluation_record = self.load_json(evaluation_path)
        if evaluation_record is not None:
            for field in ("dataset_id", "revision", "license_review"):
                if len(str(evaluation_record.get(field, "")).strip()) < 3:
                    self.fail(
                        "EVAL_DATASET",
                        evaluation_path,
                        f"{field} must be recorded",
                    )
            if str(evaluation_record.get("revision", "")).lower() in {
                "latest",
                "main",
            }:
                self.fail(
                    "EVAL_DATASET",
                    evaluation_path,
                    "evaluation revision must be immutable",
                )
            case_count = evaluation_record.get("case_count")
            if type(case_count) is not int or case_count < 1:
                self.fail(
                    "EVAL_DATASET",
                    evaluation_path,
                    "case_count must be a positive integer",
                )
            self.require_hex_field(
                evaluation_path, evaluation_record, "cases_manifest_sha256"
            )

        adapter_path = str(adapter.get("path", ""))
        adapter_record = self.load_json(adapter_path)
        if adapter_record is not None:
            for field, expected in (
                ("enabled", adapter_enabled),
                ("format", adapter.get("format")),
                ("base_model_revision", model_revision),
            ):
                if adapter_record.get(field) != expected:
                    self.fail(
                        "ADAPTER_RECORD_MISMATCH",
                        adapter_path,
                        f"{field} differs from release/model",
                    )
            if adapter_enabled is True:
                self.require_hex_field(adapter_path, adapter_record, "adapter_sha256")
                if not HEX40.fullmatch(
                    str(adapter_record.get("training_code_revision", ""))
                ):
                    self.fail(
                        "ADAPTER_RECORD",
                        adapter_path,
                        "training_code_revision must be 40 lowercase hex",
                    )
                if str(adapter_record.get("training_dataset_revision", "")).lower() in {
                    "",
                    "latest",
                    "main",
                }:
                    self.fail(
                        "ADAPTER_RECORD",
                        adapter_path,
                        "training dataset revision must be immutable",
                    )
            else:
                if adapter_record.get("adapter_sha256") != "not-produced":
                    self.fail(
                        "ADAPTER_RECORD",
                        adapter_path,
                        "disabled adapter must say adapter_sha256=not-produced",
                    )
                for field in ("training_dataset_revision", "training_code_revision"):
                    if adapter_record.get(field) != "not-applicable":
                        self.fail(
                            "ADAPTER_RECORD",
                            adapter_path,
                            f"disabled adapter must say {field}=not-applicable",
                        )
            if len(str(adapter_record.get("license_review", "")).strip()) < 3:
                self.fail(
                    "ADAPTER_RECORD",
                    adapter_path,
                    "license_review must be recorded",
                )

        rag_path = str(rag.get("path", ""))
        rag_record = self.load_json(rag_path)
        if rag_record is not None:
            if rag_record.get("enabled") != rag_enabled:
                self.fail(
                    "RAG_RECORD_MISMATCH",
                    rag_path,
                    "enabled differs from release",
                )
            for field in ("corpus_version", "index_version"):
                if rag_record.get(field) != rag.get(field):
                    self.fail(
                        "RAG_RECORD_MISMATCH",
                        rag_path,
                        f"{field} differs from release",
                    )
            if rag_record.get("authorization_filter_stage") != "before-prompt":
                self.fail(
                    "RAG_AUTHORIZATION_STAGE",
                    rag_path,
                    "authorization filtering must occur before prompt construction",
                )
            if rag_enabled is True:
                self.require_hex_field(
                    rag_path, rag_record, "chunker_configuration_sha256"
                )
                self.require_hex_field(rag_path, rag_record, "index_sha256")
                if str(rag_record.get("embedding_model_revision", "")).lower() in {
                    "",
                    "latest",
                    "main",
                }:
                    self.fail(
                        "RAG_RECORD",
                        rag_path,
                        "embedding model revision must be immutable",
                    )
            else:
                for field in ("chunker_configuration_sha256", "index_sha256"):
                    if rag_record.get(field) != "not-produced":
                        self.fail(
                            "RAG_RECORD",
                            rag_path,
                            f"disabled RAG must say {field}=not-produced",
                        )
                if rag_record.get("embedding_model_revision") != "not-applicable":
                    self.fail(
                        "RAG_RECORD",
                        rag_path,
                        "disabled RAG must say embedding_model_revision=not-applicable",
                    )
            if len(str(rag_record.get("license_review", "")).strip()) < 3:
                self.fail(
                    "RAG_RECORD",
                    rag_path,
                    "license_review must be recorded",
                )

    def check_bound_hash(self, rel: str, expected: str, code: str) -> None:
        try:
            rel = safe_relative(rel)
        except ValueError as error:
            self.fail("UNSAFE_PATH", "release.json", str(error))
            return
        if not HEX64.fullmatch(expected):
            self.fail(f"{code}_DIGEST", "release.json", f"invalid SHA-256 for {rel}")
        if not self.workspace.exists(rel):
            self.fail(f"{code}_MISSING", rel, "bound artifact is missing")
        elif self.workspace.sha256(rel) != expected:
            self.fail(f"{code}_HASH_MISMATCH", rel, "release hash differs from artifact bytes")

    def validate_topology(self) -> None:
        contract_topology = self.contract.get("serving_topology")
        environment = self.environment
        serving = self.release.get("serving", {})
        if environment.get("serving_topology") != contract_topology:
            self.fail("TOPOLOGY_MISMATCH", "environment.json", "topology differs from contract")
        if serving.get("topology") != contract_topology:
            self.fail("TOPOLOGY_MISMATCH", "release.json", "topology differs from contract")
        config_path = str(serving.get("configuration_path", ""))
        config = self.load_json(config_path)
        if config is None:
            return
        values = (
            config.get("tensor_parallel_size"),
            config.get("pipeline_parallel_size"),
            config.get("data_parallel_size"),
            environment.get("nodes"),
            environment.get("gpus_per_node"),
        )
        if any(type(value) is not int for value in values):
            self.fail("TOPOLOGY_NUMBERS", config_path, "parallel and node counts must be integers")
            return
        tp, pp, dp, nodes, gpus_per_node = values
        if min(tp, pp, dp, nodes, gpus_per_node) < 1:
            self.fail("TOPOLOGY_NUMBERS", config_path, "parallel and node counts must be positive")
            return
        if contract_topology == "one-gpu":
            if (tp, pp, dp, nodes, gpus_per_node) != (1, 1, 1, 1, 1):
                self.fail(
                    "ONE_GPU_ARITHMETIC",
                    config_path,
                    "one-gpu path requires TP=PP=DP=nodes=GPUs-per-node=1",
                )
        elif contract_topology == "three-node":
            if nodes != 3 or gpus_per_node != 1 or tp * pp != 3 or dp != 1:
                self.fail(
                    "THREE_NODE_ARITHMETIC",
                    config_path,
                    "three-node model split requires three one-GPU nodes, TP*PP=3, and DP=1",
                )
            if environment.get("interconnect") in {"", None, "nvlink"}:
                self.fail(
                    "THREE_NODE_INTERCONNECT",
                    "environment.json",
                    "record the actual network; cross-node NVLink must not be assumed",
                )

    def validate_gates(self) -> None:
        gates = self.release.get("gates")
        if not isinstance(gates, list):
            self.fail("GATES", "release.json", "gates must be an array")
            return
        seen: set[str] = set()
        evidence_paths: set[str] = set()
        for gate in gates:
            if not isinstance(gate, dict):
                self.fail("GATE_SHAPE", "release.json", "gate must be an object")
                continue
            name = str(gate.get("name", ""))
            if name in seen:
                self.fail("DUPLICATE_GATE", "release.json", f"duplicate gate {name}")
            seen.add(name)
            if gate.get("status") != "pass":
                self.fail("GATE_NOT_PASS", "release.json", f"{name} gate is not pass")
            rel = str(gate.get("evidence_path", ""))
            if rel in evidence_paths:
                self.fail(
                    "DUPLICATE_GATE_EVIDENCE",
                    "release.json",
                    f"multiple gates use {rel}",
                )
            evidence_paths.add(rel)
            evidence = self.load_json(rel)
            if evidence is None:
                self.fail(f"{name.upper()}_EVIDENCE_MISSING", rel, "gate evidence is missing")
                continue
            digest = str(gate.get("evidence_sha256", ""))
            if not HEX64.fullmatch(digest):
                self.fail("GATE_DIGEST", "release.json", f"{name} evidence digest is invalid")
            elif self.workspace.sha256(rel) != digest:
                self.fail("GATE_HASH_MISMATCH", rel, f"{name} evidence bytes differ from release")
            self.validate_common_evidence(name, rel, evidence)
            validator = getattr(self, f"validate_{name}_evidence", None)
            if validator is not None:
                validator(rel, evidence)
        missing = sorted(REQUIRED_GATES - seen)
        extra = sorted(seen - REQUIRED_GATES)
        if missing or extra:
            self.fail("GATE_SET", "release.json", f"missing={missing}, extra={extra}")

    def validate_common_evidence(
        self, name: str, rel: str, evidence: dict[str, Any]
    ) -> None:
        if evidence.get("schema_version") != 1:
            self.fail("EVIDENCE_SCHEMA", rel, "schema_version must be 1")
        if evidence.get("project_id") != self.contract.get("project_id"):
            self.fail("EVIDENCE_ID_MISMATCH", rel, "project_id differs")
        if evidence.get("release_id") != self.contract.get("release_id"):
            self.fail("EVIDENCE_ID_MISMATCH", rel, "release_id differs")
        if evidence.get("evidence_type") != name:
            self.fail("EVIDENCE_TYPE_MISMATCH", rel, "evidence_type differs from gate")
        if evidence.get("status") != "pass":
            self.fail("EVIDENCE_NOT_PASS", rel, "evidence status is not pass")
        if evidence.get("claim_scope") != self.contract.get("claim_scope"):
            self.fail("EVIDENCE_SCOPE_MISMATCH", rel, "claim_scope differs from contract")
        origin = evidence.get("origin")
        if self.validation_mode == "fixture" and origin != "synthetic":
            self.fail("FIXTURE_ORIGIN", rel, "fixture evidence must declare origin synthetic")
        if self.validation_mode == "operator-run" and origin != "observed":
            self.fail("OPERATOR_EVIDENCE_ORIGIN", rel, "operator evidence must be observed")
        attestation = evidence.get("attestation", {})
        if not isinstance(attestation, dict):
            self.fail("ATTESTATION", rel, "attestation must be an object")
            return
        for key in ("actor", "command", "result_source"):
            if len(str(attestation.get(key, "")).strip()) < 3:
                self.fail("ATTESTATION", rel, f"attestation.{key} is missing")
        if not parse_time(attestation.get("observed_at")):
            self.fail("ATTESTATION_TIME", rel, "observed_at is not an ISO-8601 timestamp")
        live = attestation.get("live_environment")
        if self.validation_mode == "fixture" and live is not False:
            self.fail("FABRICATED_LIVE_CLAIM", rel, "synthetic fixture cannot claim live execution")
        if self.validation_mode == "operator-run" and live is not True:
            self.fail("LIVE_EVIDENCE_REQUIRED", rel, "operator evidence must derive from the live run")

    def validate_quality_evidence(self, rel: str, value: dict[str, Any]) -> None:
        expected = self.release.get("evaluation", {}).get("dataset_sha256")
        if value.get("frozen_dataset_sha256") != expected:
            self.fail("QUALITY_DATASET_MISMATCH", rel, "quality evidence used another dataset")
        try:
            threshold = float(value["threshold"])
            candidate = float(value["candidate_value"])
            baseline = float(value["baseline_value"])
        except (KeyError, TypeError, ValueError):
            self.fail("QUALITY_METRICS", rel, "quality metrics must be numeric")
            return
        if not all(math.isfinite(item) for item in (threshold, candidate, baseline)):
            self.fail("QUALITY_METRICS", rel, "quality metrics must be finite")
            return
        if not isinstance(value.get("higher_is_better"), bool):
            self.fail("QUALITY_METRICS", rel, "higher_is_better must be boolean")
            return
        passed = candidate >= threshold if value.get("higher_is_better") else candidate <= threshold
        if not passed:
            self.fail("QUALITY_THRESHOLD", rel, "candidate does not meet the authored threshold")
        if value.get("higher_is_better") and candidate < baseline:
            self.fail("QUALITY_REGRESSION", rel, "candidate regresses below baseline")
        try:
            passed_raw = value.get("safety_cases_passed", 0)
            total_raw = value.get("safety_cases_total", 0)
            if type(passed_raw) is not int or type(total_raw) is not int:
                raise TypeError
            passed_cases = passed_raw
            total_cases = total_raw
        except TypeError:
            passed_cases, total_cases = -1, 0
        if total_cases < 1 or passed_cases != total_cases:
            self.fail("SAFETY_CASES", rel, "every frozen safety case must pass")
        self.require_hex_field(rel, value, "raw_results_sha256")

    def validate_performance_evidence(self, rel: str, value: dict[str, Any]) -> None:
        try:
            samples_raw = value.get("sample_count", 0)
            if type(samples_raw) is not int:
                raise TypeError
            samples = samples_raw
            limits = value["limits"]
            observed = value["observed"]
            checks = (
                (float(observed["p95_ttft_ms"]), float(limits["p95_ttft_ms_max"])),
                (
                    float(observed["p95_total_latency_ms"]),
                    float(limits["p95_total_latency_ms_max"]),
                ),
                (float(observed["error_rate"]), float(limits["error_rate_max"])),
            )
            input_rate = float(observed["input_tokens_per_second"])
            output_rate = float(observed["output_tokens_per_second"])
        except (KeyError, TypeError, ValueError):
            self.fail("PERFORMANCE_METRICS", rel, "performance evidence is incomplete")
            return
        numeric = [
            samples,
            input_rate,
            output_rate,
            *(item for pair in checks for item in pair),
        ]
        if not all(math.isfinite(float(item)) for item in numeric):
            self.fail("PERFORMANCE_METRICS", rel, "performance values must be finite")
            return
        if samples < 1:
            self.fail("PERFORMANCE_SAMPLES", rel, "sample_count must be positive")
        if any(observed_value < 0 or limit < 0 for observed_value, limit in checks):
            self.fail("PERFORMANCE_METRICS", rel, "latency/error values cannot be negative")
        error_observed, error_limit = checks[-1]
        if error_observed > 1 or error_limit > 1:
            self.fail("PERFORMANCE_METRICS", rel, "error rates must be between zero and one")
        if any(observed_value > limit for observed_value, limit in checks):
            self.fail("PERFORMANCE_SLO", rel, "an observed value exceeds its limit")
        if input_rate <= 0 or output_rate <= 0:
            self.fail("TOKEN_THROUGHPUT", rel, "token throughput must be positive")
        self.require_hex_field(rel, value, "workload_sha256")
        self.require_hex_field(rel, value, "raw_results_sha256")

    def validate_security_evidence(self, rel: str, value: dict[str, Any]) -> None:
        for key in (
            "anonymous_denial",
            "authenticated_unauthorized_denial",
            "authorized_request",
            "kubernetes_policy_check",
            "artifact_provenance",
            "cross_tenant_negative_cases",
        ):
            if value.get(key) != "pass":
                self.fail("SECURITY_GATE", rel, f"{key} is not pass")
        if value.get("public_exposure") is not False:
            self.fail("PUBLIC_EXPOSURE", rel, "security evidence reports public exposure")
        if value.get("threat_model_reviewed") is not True:
            self.fail("THREAT_MODEL", rel, "threat model review is not complete")
        self.require_hex_field(rel, value, "raw_results_sha256")

    def validate_reliability_evidence(self, rel: str, value: dict[str, Any]) -> None:
        for key in (
            "failure_injection",
            "bounded_degradation",
            "readiness_recovery",
            "rollback_to_known_good",
            "post_rollback_smoke",
            "reproduction_by_second_operator",
        ):
            if value.get(key) != "pass":
                self.fail("RELIABILITY_GATE", rel, f"{key} is not pass")
        self.require_hex_field(rel, value, "timeline_sha256")

    def validate_cost_evidence(self, rel: str, value: dict[str, Any]) -> None:
        try:
            budget = float(value["budget_limit"])
            estimated = float(value["estimated_total"])
            observed = float(value["observed_total"])
            gpu_limit = float(value["gpu_hours_limit"])
            gpu_observed = float(value["gpu_hours_observed"])
        except (KeyError, TypeError, ValueError):
            self.fail("COST_VALUES", rel, "cost values must be numeric")
            return
        if not all(
            math.isfinite(item)
            for item in (budget, estimated, observed, gpu_limit, gpu_observed)
        ):
            self.fail("COST_VALUES", rel, "cost values must be finite")
            return
        if budget <= 0 or gpu_limit <= 0:
            self.fail("COST_BUDGET", rel, "budget and GPU-hour limits must be positive")
        if min(estimated, observed, gpu_observed) < 0:
            self.fail("COST_VALUES", rel, "cost values cannot be negative")
        if estimated > budget or observed > budget or gpu_observed > gpu_limit:
            self.fail("COST_BUDGET_EXCEEDED", rel, "cost or GPU-hour budget was exceeded")
        if value.get("currency") not in {"USD", "EUR", "GBP"}:
            self.fail("COST_CURRENCY", rel, "currency must be an explicit supported code")
        self.require_hex_field(rel, value, "estimate_inputs_sha256")
        self.require_hex_field(rel, value, "billing_evidence_sha256")

    def validate_cleanup_evidence(self, rel: str, value: dict[str, Any]) -> None:
        before = value.get("inventory_before")
        actions = value.get("teardown_actions")
        after = value.get("inventory_after")
        residual = value.get("residual_billable_resources")
        commands = value.get("verification_commands")
        if not isinstance(before, list) or not before:
            self.fail("CLEANUP_INVENTORY", rel, "inventory_before must identify scoped resources")
        if not isinstance(actions, list) or not actions:
            self.fail("CLEANUP_ACTIONS", rel, "teardown actions are missing")
        if after != []:
            self.fail("CLEANUP_NOT_EMPTY", rel, "inventory_after must be empty")
        if residual != []:
            self.fail("RESIDUAL_BILLABLE_RESOURCES", rel, "billable resources remain")
        if not isinstance(commands, list) or not commands:
            self.fail("CLEANUP_VERIFICATION", rel, "verification commands are missing")
        for key in ("load_generators_stopped", "endpoint_removed", "gpu_capacity_released"):
            if value.get(key) is not True:
                self.fail("UNVERIFIED_CLEANUP", rel, f"{key} is not true")
        self.require_hex_field(rel, value, "inventory_sha256")

    def require_hex_field(self, rel: str, value: dict[str, Any], key: str) -> None:
        if not HEX64.fullmatch(str(value.get(key, ""))):
            self.fail("EVIDENCE_DIGEST", rel, f"{key} must be 64 lowercase hex")

    def validate_promotion(self) -> None:
        promotion = self.release.get("promotion")
        if not isinstance(promotion, dict):
            self.fail("PROMOTION", "release.json", "promotion must be an object")
            return
        if promotion.get("candidate_status") != "pass":
            self.fail("CANDIDATE_PROMOTION", "release.json", "candidate_status is not pass")
        if promotion.get("production_status") != "pass":
            self.fail("PRODUCTION_PROMOTION", "release.json", "production_status is not pass")
        known_good = str(promotion.get("known_good_release_id", ""))
        rollback = str(promotion.get("rollback_target_release_id", ""))
        if not known_good or rollback != known_good:
            self.fail("ROLLBACK_TARGET", "release.json", "rollback target must equal known-good release")
        if known_good == self.contract.get("release_id"):
            self.fail("ROLLBACK_TARGET", "release.json", "rollback target must precede candidate")
        if not HEX40.fullmatch(str(promotion.get("gitops_revision", ""))):
            self.fail("GITOPS_REVISION", "release.json", "GitOps revision must be 40 lowercase hex")

    def validate_kubernetes(self, rel: str) -> None:
        try:
            rel = safe_relative(rel)
        except ValueError as error:
            self.fail("UNSAFE_PATH", "contract.json", str(error))
            return
        if not self.workspace.exists(rel):
            self.fail("KUBERNETES_MANIFEST_MISSING", rel, "manifest is missing")
            return
        try:
            text = self.workspace.text(rel)
        except UnicodeDecodeError:
            self.fail("KUBERNETES_MANIFEST_ENCODING", rel, "manifest must be UTF-8")
            return
        lower = text.lower()
        unsafe_patterns = {
            "PUBLIC_EXPOSURE": (
                r"\bkind:\s*Ingress\b",
                r"\btype:\s*(?:LoadBalancer|NodePort)\b",
                r"\bexternalIPs\s*:",
            ),
            "UNSAFE_POD": (
                r"\bhostNetwork:\s*true\b",
                r"\bhostPID:\s*true\b",
                r"\bhostIPC:\s*true\b",
                r"\bhostPort\s*:",
                r"\bhostPath\s*:",
                r"\bprivileged:\s*true\b",
                r"\ballowPrivilegeEscalation:\s*true\b",
            ),
        }
        for code, patterns in unsafe_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    self.fail(code, rel, f"unsafe Kubernetes pattern matched: {pattern}")
        required_snippets = {
            "PRIVATE_SERVICE": "type: ClusterIP",
            "DEFAULT_DENY": "name: default-deny",
            "NETWORK_POLICY": "kind: NetworkPolicy",
            "NON_ROOT": "runAsNonRoot: true",
            "READ_ONLY_ROOT": "readOnlyRootFilesystem: true",
            "NO_TOKEN": "automountServiceAccountToken: false",
            "NO_PRIVILEGE_ESCALATION": "allowPrivilegeEscalation: false",
            "SECCOMP": "type: RuntimeDefault",
            "DROP_CAPABILITIES": "drop:",
            "DROP_ALL_CAPABILITIES": "- ALL",
            "RESTRICTED_NAMESPACE": "pod-security.kubernetes.io/enforce: restricted",
        }
        for code, snippet in required_snippets.items():
            if snippet.lower() not in lower:
                self.fail(code, rel, f"required manifest control is absent: {snippet}")
        images = re.findall(r"^\s*image:\s*[\"']?([^\"'\s]+)", text, re.MULTILINE)
        if not images:
            self.fail("IMAGE_MISSING", rel, "no container image found")
        for image in images:
            if not IMAGE_DIGEST.fullmatch(image):
                self.fail("MUTABLE_IMAGE", rel, f"image is not digest-pinned: {image}")
        release_image = str(self.release.get("image", ""))
        if images and release_image not in images:
            self.fail("IMAGE_IDENTITY_MISMATCH", rel, "manifest image differs from release")
        model_revision = str(self.contract.get("model", {}).get("revision", ""))
        if model_revision not in text:
            self.fail("MODEL_IDENTITY_MISMATCH", rel, "manifest lacks selected model revision")
        topology = str(self.contract.get("serving_topology", ""))
        if f"oms.open-model.systems/serving-topology: {topology}" not in text:
            self.fail(
                "MANIFEST_TOPOLOGY",
                rel,
                "manifest lacks the declared serving-topology annotation",
            )
        expected_workers = "1" if topology == "one-gpu" else "3"
        worker_patterns = (
            f'oms.open-model.systems/worker-count: "{expected_workers}"',
            f"oms.open-model.systems/worker-count: {expected_workers}",
        )
        if not any(pattern in text for pattern in worker_patterns):
            self.fail(
                "MANIFEST_TOPOLOGY",
                rel,
                f"manifest lacks worker-count {expected_workers}",
            )

    def scan_content(self) -> None:
        index_path = str(self.contract.get("paths", {}).get("evidence_index", ""))
        candidates = set(self.workspace.files) - {index_path}
        for rel in sorted(candidates):
            raw = self.workspace.bytes(rel)
            if b"\x00" in raw:
                continue
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            marker = UNRESOLVED.search(text)
            if marker:
                self.fail("UNRESOLVED_MARKER", rel, f"unresolved marker: {marker.group(0)}")
            for name, pattern in SECRET_PATTERNS.items():
                if pattern.search(text):
                    self.fail("CREDENTIAL_PATTERN", rel, f"possible {name} detected")


def write_report(path: Path, report: dict[str, Any], replace: bool) -> None:
    path = path.resolve()
    if path.exists() and not replace:
        raise ValueError(f"report exists; pass --replace-report to replace it: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument(
        "--overlay",
        type=Path,
        help="Teaching-only virtual mutation; no workspace files are changed.",
    )
    parser.add_argument("--require-operator-run", action="store_true")
    parser.add_argument("--json-report", type=Path)
    parser.add_argument("--replace-report", action="store_true")
    args = parser.parse_args()

    try:
        workspace = VirtualWorkspace(args.workspace)
        overlay = workspace.apply_overlay(args.overlay) if args.overlay else None
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL INPUT: {error}")
        return 2

    verifier = Verifier(workspace, args.require_operator_run)
    verifier.run()
    violations = sorted(
        verifier.violations, key=lambda item: (item.code, item.path, item.message)
    )
    qualified = (
        not violations
        and verifier.validation_mode == "operator-run"
        and args.require_operator_run
    )
    report = {
        "schema_version": 1,
        "overall_status": "pass" if not violations else "fail",
        "validation_mode": verifier.validation_mode,
        "live_release_qualified": qualified,
        "workspace": str(args.workspace.resolve()),
        "overlay": None if overlay is None else overlay.get("name"),
        "violation_count": len(violations),
        "violations": [asdict(item) for item in violations],
    }
    if args.json_report:
        try:
            write_report(args.json_report, report, args.replace_report)
        except (OSError, ValueError) as error:
            print(f"FAIL REPORT: {error}")
            return 2

    if violations:
        for item in violations:
            print(f"FAIL {item.code} [{item.path}]: {item.message}")
        print(
            f"RESULT fail mode={verifier.validation_mode} "
            f"violations={len(violations)} live_release_qualified=false"
        )
        return 1
    if qualified:
        print("RESULT pass mode=operator-run live_release_qualified=true")
    else:
        print(
            "RESULT pass mode=fixture live_release_qualified=false "
            "scope=verifier-exercise-only"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
