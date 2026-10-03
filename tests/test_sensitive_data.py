# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""The bounded sensitive-data check catches its target classes (samples built at runtime)."""

import importlib.util
import subprocess

import pytest

from conftest import ROOT

_spec = importlib.util.spec_from_file_location("check_sensitive_data", ROOT / "scripts/check_sensitive_data.py")
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)

# Samples are assembled from fragments so no secret-shaped string is stored in the repository.
SAMPLES = {
    "private_key_block": "-----BEGIN " + "RSA PRIVATE KEY-----",
    "aws_access_key_id": "AKIA" + "ABCDEFGHIJKLMNOP",
    "github_token": "ghp" + "_" + "a" * 36,
    "slack_token": "xox" + "b-" + "1234567890-abcdef",
    "llm_api_key": "sk-" + "ant-" + "x" * 40,
    "credential_assignment": "pass" + "word = '" + "hunter22hunter" + "'",
    "url_embedded_credential": "https://" + "user:pa55word" + "@example.invalid/",
    "private_ipv4": "endpoint 10." + "1.2.3",
    "private_hostname": "db.billing." + "internal",
}


def init_repo(path):
    subprocess.run(["git", "init", "-q", str(path)], check=True)


@pytest.mark.parametrize("kind", sorted(SAMPLES))
def test_content_patterns_detected(tmp_path, kind):
    init_repo(tmp_path)
    (tmp_path / "sample.txt").write_text(SAMPLES[kind] + "\n")
    assert kind in {f[2] for f in scanner.scan(tmp_path)}


@pytest.mark.parametrize("name", [".env", ".env.local", "id_rsa", "server.pem", "credentials.json", ".npmrc",
                                  ".pypirc", "service-account-prod.json", "terraform.tfstate"])
def test_forbidden_file_names_detected(tmp_path, name):
    init_repo(tmp_path)
    (tmp_path / name).write_text("placeholder\n")
    assert "forbidden_file_name" in {f[2] for f in scanner.scan(tmp_path)}


def test_clean_tree_has_no_findings(tmp_path):
    init_repo(tmp_path)
    (tmp_path / "README.md").write_text("Nothing sensitive. sha256 " + "ab" * 32 + "\n")
    assert scanner.scan(tmp_path) == []


def test_repository_itself_is_clean():
    assert scanner.scan(ROOT) == []
