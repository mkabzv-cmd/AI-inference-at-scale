#!/usr/bin/env python3
"""Static fail-closed checks for the lesson Kubernetes security contract."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    text = args.manifest.read_text(encoding="utf-8")
    required = {
        "private ClusterIP Service": "type: ClusterIP",
        "non-root execution": "runAsNonRoot: true",
        "read-only root filesystem": "readOnlyRootFilesystem: true",
        "no privilege escalation": "allowPrivilegeEscalation: false",
        "all capabilities dropped": "drop: [\"ALL\"]",
        "seccomp runtime default": "type: RuntimeDefault",
        "service account token disabled": "automountServiceAccountToken: false",
        "default-deny policy": "name: default-deny-all",
        "restricted namespace enforcement": "pod-security.kubernetes.io/enforce: restricted",
        "admission-policy namespace opt-in": "oms.open-model.systems/security-policy: enabled",
    }
    failures = [
        description
        for description, marker in required.items()
        if marker not in text
    ]
    forbidden = {
        "public LoadBalancer": "type: LoadBalancer",
        "host networking": "hostNetwork: true",
        "host PID": "hostPID: true",
        "host IPC": "hostIPC: true",
        "host port": "hostPort:",
        "privileged container": "privileged: true",
        "mutable latest tag": ":latest",
        "host path": "hostPath:",
        "public NodePort": "type: NodePort",
        "Ingress route": "kind: Ingress",
    }
    failures.extend(
        description
        for description, marker in forbidden.items()
        if marker in text
    )
    images = re.findall(
        r"^\s*image:\s*[\"']?([^\"'\s]+)",
        text,
        re.MULTILINE,
    )
    if not images:
        failures.append("workload image is missing")
    for image in images:
        if re.fullmatch(
            r"[A-Za-z0-9._/:-]+@sha256:[0-9a-f]{64}",
            image,
        ) is None:
            failures.append(f"workload image is not pinned by digest: {image}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: private, digest-pinned, restricted workload controls are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
