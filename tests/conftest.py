# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

# Keep released bundles free of bytecode caches (the bundle check has no ignore list).
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
TOOL_DIR = ROOT / "tools" / "commons-export-lint"
TOOL_PATH = TOOL_DIR / "commons_export_lint.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lint = _load("commons_export_lint", TOOL_PATH)


@pytest.fixture(scope="session")
def root():
    return ROOT


@pytest.fixture(scope="session")
def cel():
    return lint


@pytest.fixture
def release_copy(tmp_path):
    """Copy a fixture release into tmp_path and return a small mutation helper."""

    counter = iter(range(1000))

    class Release:
        def __init__(self, name="valid/VALID-01-commons-native-p3-none"):
            self.dir = tmp_path / f"release-{next(counter)}"
            shutil.copytree(ROOT / "fixtures" / name, self.dir)
            self.manifest_path = self.dir / "manifest.json"
            self.receipt_path = self.dir / "clearance-receipt.json"
            self.bundle = self.dir / "bundle"

        def load(self, which="manifest"):
            return json.loads((self.manifest_path if which == "manifest" else self.receipt_path).read_text())

        def save(self, obj, which="manifest"):
            path = self.manifest_path if which == "manifest" else self.receipt_path
            path.write_bytes(lint.canonical_json_bytes(obj))

        def edit(self, fn, which="manifest"):
            obj = self.load(which)
            fn(obj)
            self.save(obj, which)

        def both(self, field, value):
            self.edit(lambda m: m.__setitem__(field, value))
            self.edit(lambda r: r.__setitem__(field, value), "receipt")

        def codes(self):
            receipt = self.receipt_path if self.receipt_path.exists() else None
            return sorted({f.code for f in lint.check_release(self.manifest_path, receipt, self.bundle)})

    return Release
