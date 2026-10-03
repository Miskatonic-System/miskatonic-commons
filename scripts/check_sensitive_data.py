#!/usr/bin/env python3
# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Bounded secret and sensitive-data check for this repository.

Scans tracked and untracked-but-not-ignored files (or every file when Git is
unavailable) for common credential formats, private keys, credential and
environment file names, and obvious private network endpoints.

This is a bounded heuristic. No findings does NOT prove that no secret exists.

Usage: python scripts/check_sensitive_data.py [ROOT]
Exit status: 0 = no findings, 1 = findings.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
import sys
from pathlib import Path

CONTENT_PATTERNS = (
    ("private_key_block", r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY(?: BLOCK)?-----"),
    ("aws_access_key_id", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    ("github_token", r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    ("github_fine_grained_token", r"\bgithub_pat_[A-Za-z0-9_]{50,}\b"),
    ("slack_token", r"\bxox[abposr]-[A-Za-z0-9-]{10,}\b"),
    ("google_api_key", r"\bAIza[0-9A-Za-z_-]{35}\b"),
    ("stripe_live_key", r"\b[rs]k_live_[0-9A-Za-z]{20,}\b"),
    ("llm_api_key", r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{32,}\b"),
    ("jwt", r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    ("credential_assignment",
     r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\b\s*[:=]\s*[\"'][^\"'\s]{8,}[\"']"),
    ("url_embedded_credential", r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s:@]+@"),
    ("private_ipv4",
     r"(?<![\d.])(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(?![\d.])"),
    ("private_hostname", r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:internal|corp|intranet|lan)\b"),
)

FORBIDDEN_NAMES = (
    ".env", ".env.*", "*.env", ".envrc",
    "*.pem", "*.key", "*.p12", "*.pfx", "*.jks", "*.keystore", "*.kdbx",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "*.ppk",
    "credentials", "credentials.json", "credentials.yml", "credentials.yaml",
    "secrets.json", "secrets.yml", "secrets.yaml", "secrets.toml",
    "service-account*.json", ".npmrc", ".pypirc", ".netrc", ".git-credentials",
    ".htpasswd", "*.tfstate", "*.tfvars",
)

MAX_BYTES = 5 * 1024 * 1024


def list_files(root: Path) -> list:
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                             cwd=root, check=True, capture_output=True).stdout
        return sorted({root / p for p in out.decode("utf-8").split("\0") if p})
    except (OSError, subprocess.CalledProcessError):
        return sorted(p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts)


def scan(root: Path) -> list:
    findings = []
    compiled = [(name, re.compile(rx)) for name, rx in CONTENT_PATTERNS]
    for path in list_files(root):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        for pattern in FORBIDDEN_NAMES:
            if fnmatch.fnmatch(path.name, pattern):
                findings.append((rel, 0, "forbidden_file_name", pattern))
        if path.stat().st_size > MAX_BYTES:
            findings.append((rel, 0, "oversized_file_not_scanned", str(path.stat().st_size)))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append((rel, 0, "binary_file_not_scanned", "binary files are not expected here"))
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for name, rx in compiled:
                if rx.search(line):
                    findings.append((rel, lineno, name, "pattern matched (value not printed)"))
    return findings


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]).resolve() if argv else Path(__file__).resolve().parent.parent
    findings = scan(root)
    for rel, lineno, name, detail in findings:
        print(f"{rel}:{lineno}: {name}: {detail}")
    print(f"scanned root: {root.name}; findings: {len(findings)}")
    print("note: absence of findings does not prove absence of secrets")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
