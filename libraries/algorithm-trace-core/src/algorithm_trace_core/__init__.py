# Copyright 2026 The Miskatonic Commons Authors
# SPDX-License-Identifier: Apache-2.0
"""AlgorithmTrace v0.4 Public Core.

A generic execution-trace substrate: typed ARRAY/SCALAR storage events, canonical JSONL,
content-addressed trace profiles, a generic recorder, a deterministic replay/reference
validator and logical metrics. Domain meaning lives in profiles, not in this core.

Protocol identifiers use the ``algorithm-trace-core`` namespace. This package is a public
derivative; it is not the canonical research source of the protocol.
"""

TRACE_SCHEMA_VERSION = "algorithm-trace-core.algorithm-trace.v0.4"
RUN_SCHEMA_VERSION = "algorithm-trace-core.algorithm-run.v0.4"
INSTRUMENTATION_VERSION = "algorithm-trace-core.instrumented-storage.v0.4"
CORE_VERSION = "algorithm-trace-core.algorithm-trace-core.v0.4"
PROFILE_DOCUMENT_VERSION = "algorithm-trace-core.trace-profile.v0.4"

__version__ = "0.1.0"
PROTOCOL_VERSION = "0.4"
