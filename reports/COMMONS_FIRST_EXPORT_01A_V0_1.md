# First private-origin export: AlgorithmTrace v0.4 Public Core (01A)

Work order: WO-COMMONS-FIRST-EXPORT-01A
Package: `algorithm-trace-core` 0.1.0 (protocol 0.4), at `libraries/algorithm-trace-core/`

Fact classes used below:

- **[S]** private source fact (established privately; bound here by digest);
- **[R]** publicly reproducible fact (anyone can check it from this repository);
- **[P]** provider-observed fact;
- **[A]** policy assertion;
- **[C]** commercial opinion or adjudication.

## Origin and clearance

- **[S]** Origin is Miskatonic-System/msk-algorithms at frozen commit
  `449bfdb2e823993c699a033d8a75e3c8171f9176`.
- **[S]** The allowlist is 11 files: 3 v0.4 schemas, 5 generic `trace_v04`
  modules, `canonical.py`, and two historical modules that contribute only 6
  symbols.
- **[S]** The import closure stays within the allowlist, so no scope expansion
  was needed.
- **[S]** The source clearance was independently reviewed (one REVISE round,
  then accepted with limitations) and merged in the origin as `391e5171`.
  Disposition: `ALGORITHMTRACE_V0_4_PUBLIC_CORE_SOURCE_CLEARED`.
- **[R]** `libraries/algorithm-trace-core/PROVENANCE.json` binds the clearance
  receipt by SHA-256, together with every source file's blob SHA and SHA-256
  and every extracted symbol's line range.

## What was exported, and how [R]

`PROVENANCE.json` classifies all 22 bundle files:

| Class | Files |
| --- | --- |
| Surgically extracted | `framing.py`: the 6 symbols, each AST-equal to its source; `load_schema`'s package-resource name adapted |
| Packaging adaptation | `canonical.py` and `metrics.py` (SPDX header only); `recorder.py`, `replay.py`, `profiles.py`, `__init__.py`; the 3 schemas |
| Commons-native | the synthetic example profile and its semantics module, the demo, the tests, README, packaging, LICENSE and NOTICE |

Protocol identifiers moved from the origin namespace to
`algorithm-trace-core.*` through a 7-entry substitution table. The private
values are withheld and the table is bound by SHA-256.

## Not exported

- domain profiles and their semantics modules;
- every algorithm implementation;
- harnesses and procedure-conformance models;
- freeze documents and source-binding receipts;
- experiments, evidence, corpora and reports;
- work orders and review records;
- agent instructions and the roadmap;
- all private Git history.

## Parity [S]

A private harness ran the frozen source, with only the substitution table
applied, side by side with this package:

| Check | Result |
| --- | --- |
| P1 canonical JSON | 21/21 |
| P2 JSONL framing | 6/6 |
| P3 recorder events and seals | 12/12 |
| P4 run id | 10/10 |
| P5 replay acceptance | 6/6 |
| P6 replay rejection (23 hostile cases, identical codes) | 23/23 |
| P7 profile digest (the example and all 14 private profile documents: 16 digest comparisons plus 1 catalog-identity check) | 17/17 |
| P8 metrics | 6/6 |
| Extracted-symbol AST equality | 6/6 |
| Header-only copies byte-identical in body | 2/2 |

The report is bound in `PROVENANCE.json` by SHA-256. Two divergences are
documented:

- `executed_path` no longer hard-codes the origin's layout;
- the profile catalog is configurable.

## Public tests [R]

The library's own suite (34 tests) runs inside the Commons suite. It covers:

- the synthetic `INTEGER_SEQUENCE_EXAMPLE` demonstrator, including recording,
  replay, metrics, exact profile resolution and a reproducible profile
  document;
- 23 hostile controls, each rejected with its stable code;
- an import allowlist covering only the standard library and the three
  declared dependencies, so there is no network or telemetry path;
- a URL and namespace allowlist.

## Security [R]/[S]

Over both the source allowlist and the public bundle:

- gitleaks and the Commons sensitive-data check found 0 findings;
- a targeted scan for usernames, local paths, machine names, internal hosts,
  hidden files and PR or issue links found 0 findings.

An earlier draft test spelled out a withheld private identifier while
asserting its absence. That test was replaced by a structural allowlist
before any public commit.

## Commercial [C]

The organization's commercial-review function recorded the related family as
`UNCERTAIN`, `export_authorized: false`. This is a registry-wide default label.
The work order required a stop. The repository owner adjudicated
**COMPLEMENTARY**. Both the label and the decision are recorded in the private
clearance receipt.

Minimum viable moat: domain profiles, research infrastructure, organization-wide
custody and provenance, managed verification, governance, integrations,
hosting, private deployment, assurance and support all remain outside this
primitive. Nothing was withheld to create scarcity.

## Claim boundary [A]

This release shows that a generic trace substrate was cleared and published
under its recorded scope. It does **not** establish:

- that all of the origin is publishable, or that any other artifact is
  cleared;
- that future profiles are public;
- any automatic synchronization with the origin;
- inherited research authority, universality, or correctness or optimality of
  anything traced;
- market demand, willingness to pay, commercial support or security
  certification;
- that private history is safe to expose.

`DIGEST_IDENTITY != PUBLICATION_OF_PRIVATE_HISTORY`.
`PUBLIC_DERIVATIVE != CANONICAL_RESEARCH_SOURCE`.

Recorded limitation: the Commons claim scan flags the moat-surface enum value
`SLA` as claim language. It was omitted from the receipt's retained surfaces;
`SUPPORT` and the analysis text cover it.
