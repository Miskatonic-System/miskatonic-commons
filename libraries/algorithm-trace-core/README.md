# algorithm-trace-core

AlgorithmTrace v0.4 Public Core (protocol 0.4, package 0.1.1) is a small Python library for
recording and checking execution traces of programs that operate on declared storage.

It provides:

- **a typed trace format.** `RUN_BEGIN`, `READ`, `WRITE`, `SWAP`, `COMPARE`, `FRAME_ENTER`,
  `FRAME_EXIT` and `RUN_END` events over declared `ARRAY` and `SCALAR` storage, with typed values
  (`INTEGER`, `TAGGED_ITEM`, `EMPTY`);
- **canonical JSONL.** Every line is RFC 8785 canonical JSON and the file ends with one LF.
  Traces are identified by SHA-256;
- **content-addressed profiles.** A profile document (JSON) defines the problem, precondition,
  result and storage shapes, the permitted operations and the comparison mode. Its identity is
  SHA-256 of its RFC 8785 bytes. It pins the SHA-256 of the Python module that gives it meaning;
- **a generic recorder.** It emits canonical events, derives a run id that binds the profile,
  problem, storage and identity, and seals a run record;
- **a deterministic replay/reference validator.** It rebuilds state from the trace bytes alone
  and checks framing, schema, sequence, identity, profile resolution, storage, read values, writes,
  swaps, comparisons, frames and the result. It rejects a bad trace with a stable error `code`;
- **logical metrics.** Reads, writes, comparisons, swaps, events and frame depth, derived from
  the events.

Generic event semantics are kept apart from profile semantics. The core knows nothing about
any particular algorithm or domain.

## Quick start

```sh
python -m pip install ./libraries/algorithm-trace-core
```

```python
from algorithm_trace_core.examples.running_maximum import record, result_of
from algorithm_trace_core.replay import replay_v04
from algorithm_trace_core.metrics import derive_metrics_v04

rec = record([3, -1, 7, 2], floor=1)
result = result_of(rec)
rec.finish(result)
trace_bytes, digest, run_record = rec.seal(None, "0" * 64, "example", result)
replayed = replay_v04(trace_bytes, expected_digest=digest, run_record=run_record)
print(derive_metrics_v04(replayed.events))
```

`INTEGER_SEQUENCE_EXAMPLE` and the running-maximum workload are synthetic examples written for
this package. They demonstrate the core. They are not benchmarks.

Your own profiles live in your own directories. Pass `profile_dirs=[...]` to `replay_v04`,
`resolve` and `profile_for`. Python must be able to import the semantics module a profile names,
and its bytes must match the pinned SHA-256. Locating that module imports its parent packages,
but the module itself is imported only after its digest matches. The pin covers the module file
only. Parent packages run before the check, so install only semantics packages you trust.

## Errors

`replay_v04` reports every rejected trace as a `ReplayError` with a stable `code`. Two
boundaries are deliberate:

- **Profile module discovery.** If a parent package raises while the semantics module is being
  located, replay reports `PROFILE_MODULE_RESOLUTION_FAILED` (since 0.1.1). A parent that raises
  `ImportError`, or a module that cannot be found, is reported as `PROFILE_SEMANTICS_MISMATCH`.
- **Semantics execution.** Once the pinned module has been imported, an exception it raises is
  not rewritten. It propagates unchanged, because it is a fault in that profile's code rather
  than a property of the trace.

A frame `scope` is a declared range. Replay checks that it lies inside its array storage and
inside the nearest enclosing scope on the same storage. It does not restrict which cells the
events inside the frame may access.

## What it does not establish

Passing replay shows that a trace is internally consistent with its declared storage, its
profile and the profile's semantics hooks. It does **not** show:

- that an implementation is correct, or that an algorithm is optimal;
- that the core covers arbitrary algorithm domains. Each domain needs its own profile, and
  every profile is a separate claim;
- that a hash or digest establishes where source code came from or who produced a trace.
  Digests bind bytes, not authors;
- any scientific result;
- that the library is production-secure or suitable for safety-critical use.

## Origin

This package is a public derivative of a generic trace core developed in a private research
repository. The extraction is limited to the generic substrate and was cleared for Apache-2.0
publication. [`PROVENANCE.json`](PROVENANCE.json) records:

- the exact source commit;
- the source files and their digests;
- how each public file was produced;
- the private-to-public parity results.

The private repository remains the canonical research source of the protocol. This package
inherits none of its research authority.

Protocol identifiers use the `algorithm-trace-core.` namespace, so traces made with this package
are distinguishable from traces made with the private source.

## Changes

- **0.1.1** (maintenance). Profile module discovery failures now stay inside the error envelope
  (`PROFILE_MODULE_RESOLUTION_FAILED`). Forty hostile controls were added that reach the generic
  core directly; several use a test-only `CORE_PROBE` profile whose hooks always accept. Each has
  a positive twin that must replay cleanly. Replay acceptance is otherwise unchanged.
- **0.1.0.** First release.

## Support

This is a public open-source reference and utility, maintained on a best-effort basis. It is
not a commercial product, a managed or SLA-backed service, or a security or scientific
certification. It collects no telemetry, makes no network calls, and needs no account or private
repository.

## License

Apache License 2.0. See `LICENSE` and `NOTICE`.
