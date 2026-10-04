# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""Run each library's own test suite in a separate pytest process (keeps conftest modules isolated)."""

import os
import subprocess
import sys

import pytest

from conftest import ROOT

LIBRARIES = sorted(p.parent for p in (ROOT / "libraries").glob("*/tests"))


@pytest.mark.parametrize("library", LIBRARIES, ids=lambda p: p.name)
def test_library_suite_passes(library):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(library / "tests")],
                          cwd=library, capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stdout[-4000:] + proc.stderr[-2000:]
