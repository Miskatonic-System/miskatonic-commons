# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Repository-level bootstrap contract (work-order tests T12-T20)."""

import ast
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import ROOT, TOOL_DIR, TOOL_PATH, lint

WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.y*ml"))
CLEAN_HISTORY = json.loads((ROOT / "provenance/BOOTSTRAP_CLEAN_HISTORY_RECEIPT_V0_1.json").read_text())
RECORDED_ROOT = CLEAN_HISTORY["root_commit"]["sha"]

ALLOWED_TOOL_IMPORTS = {"__future__", "argparse", "hashlib", "json", "os", "re", "stat", "sys", "pathlib"}


def git(*args, cwd=ROOT):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def in_git_checkout():
    if shutil.which("git") is None:
        return False
    try:
        return git("rev-parse", "--show-toplevel") == str(ROOT)
    except subprocess.CalledProcessError:
        return False


def tracked_text_files():
    if in_git_checkout():
        names = git("ls-files").splitlines()
        paths = [ROOT / n for n in names]
    else:
        paths = [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]
    out = []
    for p in paths:
        try:
            out.append((p, p.read_text(encoding="utf-8")))
        except (UnicodeDecodeError, FileNotFoundError):
            pass
    return out


def tool_imports():
    tree = ast.parse(TOOL_PATH.read_text())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add((node.module or "").split(".")[0])
        elif isinstance(node, ast.Call) and getattr(node.func, "id", None) in ("__import__", "eval", "exec"):
            names.add(f"<dynamic:{node.func.id}>")
    return names


# T12 ------------------------------------------------------------------------

def test_t12_tool_imports_no_network_capable_modules():
    assert tool_imports() <= ALLOWED_TOOL_IMPORTS


def test_t12_tool_runs_with_network_disabled(monkeypatch, capsys):
    def refuse(*args, **kwargs):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    assert lint.main(["check-index", "--index", str(ROOT / "releases/package-index-v0.1.json"),
                      "--repo-root", str(ROOT)]) == 0
    assert lint.main(["replay-fixtures", str(ROOT / "fixtures"),
                      "--expected", str(ROOT / "fixtures/expected-results.json")]) == 0
    capsys.readouterr()


def test_t12_standalone_tool_runs_isolated_from_repository(tmp_path):
    """Copy only the bundle somewhere else and run it with -I (isolated mode)."""
    bundle = tmp_path / "commons-export-lint"
    shutil.copytree(TOOL_DIR, bundle, ignore=shutil.ignore_patterns("__pycache__"))
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.run([sys.executable, "-I", str(bundle / "commons_export_lint.py"), "check-release",
                           "--manifest", str(ROOT / "releases/commons-export-lint/0.1.0/manifest.json"),
                           "--receipt", str(ROOT / "releases/commons-export-lint/0.1.0/clearance-receipt.json"),
                           "--bundle-root", str(bundle)],
                          capture_output=True, text=True, env=env, cwd=tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr


# T13 ------------------------------------------------------------------------

def test_t13_no_private_repository_is_referenced_or_required():
    """The only organization repository named anywhere in tracked files is Commons itself."""
    offenders = []
    for path, text in tracked_text_files():
        for match in re.finditer(r"Miskatonic-System/([A-Za-z0-9._-]+)", text):
            if match.group(1) != "miskatonic-commons":
                offenders.append(f"{path.relative_to(ROOT)}: {match.group(0)}")
    assert offenders == []


def test_t13_tests_and_scripts_need_no_credentials_or_remote_clones():
    pattern = re.compile(r"git clone (?!--)|GITHUB_TOKEN|\bsecrets\.[A-Z_]|ssh://|git@github\.com")
    for path in list((ROOT / "tests").glob("*.py")) + list((ROOT / "scripts").glob("*.py")):
        if path.name == Path(__file__).name:
            continue
        assert not pattern.search(path.read_text()), path.name


# T14 ------------------------------------------------------------------------

def test_t14_fixture_replay_is_deterministic():
    first = lint.canonical_json_bytes(lint.replay_fixtures(ROOT / "fixtures"))
    second = lint.canonical_json_bytes(lint.replay_fixtures(ROOT / "fixtures"))
    assert first == second == (ROOT / "fixtures/expected-results.json").read_bytes()


def test_t14_fixture_generation_is_deterministic(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "scripts/generate_fixtures.py"), str(tmp_path)],
                   check=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    generated = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    committed = sorted(p.relative_to(ROOT / "fixtures") for p in (ROOT / "fixtures").rglob("*") if p.is_file())
    assert generated == committed
    for rel in generated:
        assert (tmp_path / rel).read_bytes() == (ROOT / "fixtures" / rel).read_bytes(), rel


def test_t14_release_metadata_is_reproducible():
    proc = subprocess.run([sys.executable, str(ROOT / "scripts/build_release_metadata.py"), "--check"],
                          capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    assert proc.returncode == 0, proc.stdout


def test_t14_all_json_is_canonical():
    for path, text in tracked_text_files():
        if path.suffix == ".json":
            assert lint.canonical_json_bytes(json.loads(text)) == text.encode("utf-8"), path


# T15 ------------------------------------------------------------------------

def test_t15_apache_license_and_notice_present():
    license_text = (ROOT / "LICENSE").read_text()
    assert "Apache License" in license_text and "Version 2.0, January 2004" in license_text
    assert "TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION" in license_text
    assert "Grant of Patent License" in license_text
    notice = (ROOT / "NOTICE").read_text()
    assert "Apache License, Version 2.0" in notice
    assert "no rights to use Miskatonic names" in notice


def test_t15_license_is_byte_identical_to_root_commit():
    raw = (ROOT / "LICENSE").read_bytes()
    blob = hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest()
    recorded = {f["path"]: f["blob"] for f in CLEAN_HISTORY["root_commit"]["files"]}
    assert blob == recorded["LICENSE"]


def test_t15_bundle_ships_license_and_notice():
    for name in ("LICENSE", "NOTICE"):
        assert (TOOL_DIR / name).read_bytes() == (ROOT / name).read_bytes()
    manifest = json.loads((ROOT / "releases/commons-export-lint/0.1.0/manifest.json").read_text())
    assert set(manifest["notices"]) == {"LICENSE", "NOTICE"}
    assert manifest["license"] == "Apache-2.0"


def test_t15_bundled_schemas_match_repository_schemas():
    for schema in (ROOT / "schemas").glob("*.json"):
        assert (TOOL_DIR / "schemas" / schema.name).read_bytes() == schema.read_bytes()


def test_t15_source_files_carry_spdx_headers():
    for path, text in tracked_text_files():
        if path.suffix == ".py":
            assert "SPDX-License-Identifier: Apache-2.0" in text[:400], path


def test_t15_dependencies_pinned_with_hashes():
    lines = (ROOT / "requirements-dev.txt").read_text().splitlines()
    pins = [l for l in lines if l and not l.startswith(("#", " "))]
    assert pins
    for pin in pins:
        assert re.match(r"^[a-z0-9._-]+==[^\s]+ \\$", pin), pin
    assert "jsonschema==" in "\n".join(pins) and "pytest==" in "\n".join(pins)


# T16 / T18 -------------------------------------------------------------------

def test_t16_ci_never_publishes():
    forbidden = re.compile(
        r"pypi|twine|npm publish|docker push|ghcr\.io|gh release|softprops|"
        r"upload-release|id-token|packages:\s*write|contents:\s*write|marketplace", re.I)
    assert WORKFLOWS
    for wf in WORKFLOWS:
        assert not forbidden.search(wf.read_text()), wf.name


def test_t16_t39_workflows_are_fork_safe():
    for wf in WORKFLOWS:
        text = wf.read_text()
        assert "pull_request_target" not in text and "workflow_run" not in text, wf.name
        assert "secrets." not in text, wf.name
        assert re.search(r"^permissions:\n  contents: read\n", text, re.M), wf.name
        for use in re.findall(r"uses:\s*(\S+)", text):
            assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", use), f"{wf.name}: unpinned {use}"


def test_t18_no_automatic_private_backport():
    forbidden = re.compile(r"git push|repository_dispatch|gh pr create|gh api|repository:\s*\S+/|"
                           r"curl -X (POST|PUT|PATCH)")
    for wf in WORKFLOWS:
        assert not forbidden.search(wf.read_text()), wf.name
    for path in list((ROOT / "scripts").glob("*.py")) + [TOOL_PATH]:
        assert "git push" not in path.read_text(), path.name


# T17 ------------------------------------------------------------------------

def test_t17_no_telemetry_path_in_tool():
    source = TOOL_PATH.read_text()
    assert tool_imports() <= ALLOWED_TOOL_IMPORTS
    for token in ("urlopen", "http.client", "socket", "requests", "analytics", "uuid", "getpass",
                  "platform", "environ["):
        assert token not in source, token


# T19 ------------------------------------------------------------------------

def test_t19_no_private_git_ancestry():
    if not in_git_checkout():
        pytest.skip("not running inside a Git checkout of this repository")
    if git("rev-parse", "--is-shallow-repository") == "true":
        pytest.skip("shallow clone: full history required (CI uses fetch-depth: 0)")
    roots = set(git("rev-list", "--max-parents=0", "--all").split())
    assert roots == {RECORDED_ROOT}
    assert git("rev-list", "--parents", "-n", "1", RECORDED_ROOT).split() == [RECORDED_ROOT]
    assert git("replace", "-l") == ""
    assert not (ROOT / ".gitmodules").exists()
    assert not Path(git("rev-parse", "--git-path", "info/grafts")).exists()


# T20 ------------------------------------------------------------------------

def test_t20_fresh_checkout_of_head_passes_bootstrap_checks(tmp_path):
    if not in_git_checkout():
        pytest.skip("not running inside a Git checkout of this repository")
    clone = tmp_path / "fresh"
    subprocess.run(["git", "clone", "--quiet", "--no-local", str(ROOT), str(clone)], check=True)
    if not (clone / "tools/commons-export-lint/commons_export_lint.py").exists():
        pytest.skip("HEAD predates the bootstrap tree")
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"}
    tool = str(clone / "tools/commons-export-lint/commons_export_lint.py")
    for cmd in ([tool, "check-index", "--index", "releases/package-index-v0.1.json", "--repo-root", "."],
                [tool, "replay-fixtures", "fixtures", "--expected", "fixtures/expected-results.json"],
                [str(clone / "scripts/check_sensitive_data.py")]):
        proc = subprocess.run([sys.executable, "-I", *cmd], cwd=clone, capture_output=True, text=True, env=env)
        assert proc.returncode == 0, proc.stdout + proc.stderr
