#!/usr/bin/env python3
"""Scan repository candidates for high-confidence credential material.

The scanner reports only the credential category and path. It intentionally
does not print the matching text.
"""

import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CANONICAL_AWS_ACCOUNT_PLACEHOLDERS = {
    "000000000000",
    "111122223333",
    "123456789012",
}

PATTERNS = (
    (
        "AWS access key ID",
        re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    ),
    (
        "AWS secret access key assignment",
        re.compile(
            r"(?i)\baws_secret_access_key\b\s*[:=]\s*"
            r"[\"']?[A-Za-z0-9/+=]{40}(?=$|[\s\"'])"
        ),
    ),
    (
        "GitHub fine-grained token",
        re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b"),
    ),
    (
        "GitHub token",
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    ),
    (
        "Hugging Face token",
        re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
    ),
    (
        "private key",
        re.compile(
            r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
        ),
    ),
    (
        "EKS cluster endpoint",
        re.compile(
            r"https://[A-Za-z0-9-]{20,}\."
            r"(?:gr7\.)?[a-z]{2}(?:-gov)?-[a-z]+-\d+\.eks\.amazonaws\.com"
        ),
    ),
)

AWS_ACCOUNT_CONTEXT_PATTERN = re.compile(
    r"(?ix)"
    r"(?:"
    r"(?:aws[_ -]?account(?:[_ -]?id)?|account_id)\s*[:=]\s*[\"']?"
    r"|arn:aws(?:-[a-z]+)?:[a-z0-9-]*:[a-z0-9-]*:"
    r"|https?://"
    r"|(?<!\d)(?=\d{12}\.dkr\.ecr)"
    r")"
    r"(?P<account>\d{12})"
    r"(?:\b|\.dkr\.ecr)"
)


def repository_files():
    """Return tracked and non-ignored untracked regular files."""
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        ignored_directories = {
            ".git",
            ".venv",
            "artifacts",
            "__pycache__",
            "node_modules",
        }
        return sorted(
            path
            for path in ROOT.rglob("*")
            if path.is_file()
            and not ignored_directories.intersection(path.relative_to(ROOT).parts)
        )

    paths = []
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        path = ROOT / os.fsdecode(raw_path)
        if path.is_file() or path.is_symlink():
            paths.append(path)
    return sorted(paths)


def main():
    findings = []
    scanned = 0

    for path in repository_files():
        try:
            if path.is_symlink():
                data = os.fsencode(os.readlink(path))
            else:
                data = path.read_bytes()
        except OSError as error:
            print(
                f"Could not read {path.relative_to(ROOT)}: {error}",
                file=sys.stderr,
            )
            return 1

        # Do not interpret binary assets as credential-bearing source text.
        if b"\0" in data[:8192]:
            continue

        scanned += 1
        text = data.decode("utf-8", errors="replace")
        relative_path = path.relative_to(ROOT)

        for category, pattern in PATTERNS:
            if pattern.search(text):
                findings.append((category, relative_path))

        for match in AWS_ACCOUNT_CONTEXT_PATTERN.finditer(text):
            if match.group("account") not in CANONICAL_AWS_ACCOUNT_PLACEHOLDERS:
                findings.append(("possible AWS account ID", relative_path))
                break

    if findings:
        for category, relative_path in sorted(set(findings)):
            print(
                f"Possible {category} detected in {relative_path}",
                file=sys.stderr,
            )
        print(
            "Security validation failed without printing matched values",
            file=sys.stderr,
        )
        return 1

    print(
        f"Scanned {scanned} repository text file(s) for credential material"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
