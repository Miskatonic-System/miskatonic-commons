# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
import sys
from pathlib import Path

import pytest

# Keep the release bundle free of bytecode caches (the Commons bundle check has no ignore list).
sys.dont_write_bytecode = True

LIB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIB / "src"))
sys.path.insert(0, str(LIB / "tests"))

from algorithm_trace_core import canonical, framing, metrics, profiles, recorder, replay  # noqa: E402
from algorithm_trace_core import TRACE_SCHEMA_VERSION  # noqa: E402
from cases import Impl  # noqa: E402


def public_impl() -> Impl:
    return Impl(
        name="public",
        canonical_bytes=canonical.canonical_bytes,
        canonical_digest=canonical.canonical_digest,
        strict_loads=canonical.strict_loads,
        serialize_jsonl=framing.serialize_jsonl,
        recorder_cls=recorder.RecorderV04,
        frame_cls=recorder.Frame,
        derive_run_id=recorder.derive_run_id_v04,
        profile_digest=profiles.profile_digest,
        derive_metrics=metrics.derive_metrics_v04,
        replay=lambda trace, profile_dir, **kw: replay.replay_v04(trace, profile_dirs=[profile_dir], **kw),
        error_cls=framing.ReplayError,
        profile_dir=profiles.PROFILE_DIR,
        trace_schema_version=TRACE_SCHEMA_VERSION,
    )


@pytest.fixture(scope="session")
def impl() -> Impl:
    return public_impl()
