#!/usr/bin/env python3
"""Render the fixed one-GPU Deployment from a reviewed candidate."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def checked_name(value: str) -> str:
    if (
        not re.fullmatch(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?", value)
        or len(value) > 63
    ):
        raise ValueError(f"unsafe Kubernetes name: {value!r}")
    return value


parser = argparse.ArgumentParser()
parser.add_argument("--candidates", type=Path, required=True)
parser.add_argument("--candidate-id", required=True)
parser.add_argument("--image", required=True)
parser.add_argument("--nodegroup", required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
if not re.fullmatch(
    r"[A-Za-z0-9][A-Za-z0-9./:_-]*@sha256:[0-9a-f]{64}",
    args.image,
):
    raise SystemExit("--image must be an immutable OCI name@sha256 digest")
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,62}", args.nodegroup):
    raise SystemExit("--nodegroup must be a Kubernetes label value")
config = json.loads(args.candidates.read_text(encoding="utf-8"))
candidate = next(
    (
        item
        for item in config["candidates"]
        if item["id"] == args.candidate_id
    ),
    None,
)
if candidate is None:
    raise SystemExit("unknown candidate")
candidate_id = checked_name(str(candidate["id"]))
name = checked_name("vllm")
frozen = config["frozen"]
flags = [
    frozen["model_id"],
    "--revision",
    frozen["model_revision"],
    "--served-model-name",
    frozen["served_model_name"],
    "--dtype",
    frozen["dtype"],
    "--max-model-len",
    str(frozen["max_model_len"]),
    "--gpu-memory-utilization",
    str(candidate["gpu_memory_utilization"]),
    "--max-num-seqs",
    str(candidate["max_num_seqs"]),
    "--max-num-batched-tokens",
    str(candidate["max_num_batched_tokens"]),
]
if candidate["enforce_eager"]:
    flags.append("--enforce-eager")
if candidate["enable_prefix_caching"]:
    flags.append("--enable-prefix-caching")
args_yaml = "\n".join(f"            - {json.dumps(flag)}" for flag in flags)
manifest = f"""apiVersion: v1
kind: Namespace
metadata:
  name: oms-lesson-23
  labels:
    app.kubernetes.io/part-of: oms-course
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  namespace: oms-lesson-23
  labels:
    app.kubernetes.io/name: vllm
    oms.example/candidate: {candidate_id}
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app.kubernetes.io/name: vllm
  template:
    metadata:
      labels:
        app.kubernetes.io/name: vllm
        oms.example/candidate: {candidate_id}
    spec:
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: 60
      nodeSelector:
        eks.amazonaws.com/nodegroup: {json.dumps(args.nodegroup)}
      securityContext:
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: server
          image: {args.image}
          imagePullPolicy: IfNotPresent
          args:
{args_yaml}
          ports:
            - name: http
              containerPort: 8000
          resources:
            requests:
              cpu: "2"
              memory: 8Gi
              nvidia.com/gpu: "1"
            limits:
              cpu: "4"
              memory: 16Gi
              nvidia.com/gpu: "1"
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
          startupProbe:
            httpGet:
              path: /health
              port: http
            failureThreshold: 120
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: http
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /health
              port: http
            periodSeconds: 20
---
apiVersion: v1
kind: Service
metadata:
  name: vllm
  namespace: oms-lesson-23
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: vllm
  ports:
    - name: http
      port: 8000
      targetPort: http
"""
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(manifest, encoding="utf-8")
print(f"rendered {args.candidate_id} to {args.output}")
