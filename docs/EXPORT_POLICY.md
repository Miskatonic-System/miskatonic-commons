# Export Policy (v0.1)

This policy governs how any artifact comes to be published in Miskatonic
Commons.

## 1. Direction of flow

```
ORIGINATING PROJECT (canonical source)
        |
        | explicit export candidate (specific files, specific version)
        v
EXPORT CLEARANCE (independent dimensions, see section 4)
        |
        v
CLEAN PUBLIC PACKAGE (approved bytes + public release metadata)
        |
        v
MISKATONIC COMMONS
```

- Originating project -> public export is permitted **after clearance**.
- Public export -> retroactive change to the origin's evidence, results,
  execution history, acceptance gates or interpretations is **prohibited**.

Public improvements may be offered back to an originating project only
through that project's own normal engineering review. Nothing here does that
automatically.

## 2. Clean history

Commons has its own Git history, which began with a single root commit
created by GitHub when the repository was made (see
[`provenance/`](../provenance/)). The following are prohibited:

- making a private repository public in order to release part of it;
- mirroring, transplanting, grafting or filtering private Git history into
  Commons;
- subtree imports that carry private history;
- submodules that point at private repositories;
- private bundles, reflogs or historical branches.

An export consists only of approved public bytes, documentation, tests,
examples and public-safe provenance metadata. A clean source tree is not, by
itself, clearance.

## 3. What a release must contain

Every released package provides, under `releases/<package>/<version>/`:

- `manifest.json` — a
  [public release manifest](../schemas/public-release-manifest-v0.1.schema.json);
- `clearance-receipt.json` — a
  [public clearance receipt](../schemas/public-clearance-receipt-v0.1.schema.json);

and an entry in [`releases/package-index-v0.1.json`](../releases/package-index-v0.1.json).

The manifest lists every file in the bundle with its SHA-256 hash, the bundle
digest, the license, notices, a complete dependency inventory with licenses,
the release class, the commercial-impact class, the source disclosure level,
and a bounded public claim statement.

## 4. Clearance dimensions

A release needs every one of these to pass. Passing one implies nothing about
another.

| Dimension | Owner | Confirms |
| --- | --- | --- |
| A. Originating technical | The originating project | What the artifact actually does, its claim boundary, and exactly which bytes are proposed. |
| B. Provenance | Export reviewer | Exact source custody, a clean package, no undeclared private ancestry. |
| C. Security | Security reviewer | No credentials, tokens, secrets, internal endpoints, private infrastructure assumptions or sensitive configuration. |
| D. Dependency / license | License reviewer | Dependencies, licenses, redistribution rights, notices, no incompatible terms. For Apache-2.0 releases of potentially novel technology, the patent grant is explicitly acknowledged. |
| E. Commercial impact | Commercial reviewer, where applicable | Commercial impact only (see [COMMERCIAL_IMPACT.md](COMMERCIAL_IMPACT.md)). It never decides scientific or technical truth. |
| F. Public packaging | Commons maintainers | Standalone usability, public-safe documentation, tests, examples, release receipt, support boundary. |

Artifacts written directly in Commons (`COMMONS_NATIVE`) have no originating
private project; Commons maintainers own all dimensions, and the commercial
dimension may be recorded as not applicable when the commercial impact is
`NONE`.

## 5. Fail-closed rules

A release, and any future import tooling, must be rejected when any of these
holds. There is no "best effort" mode.

- the clearance receipt is missing;
- the clearance state is not `CLEARED`;
- the release class is not `P3` or `P4`;
- a bundle hash or the bundle digest does not match;
- an undeclared file is present, or a declared file is missing;
- license information is missing;
- the source disclosure level is incompatible with the metadata (for example
  an opaque release that names or locates its origin);
- commercial impact is `UNCERTAIN`;
- a higher-risk commercial class lacks a recorded moat review or human
  authorization;
- the public claim boundary is absent;
- release text claims scientific, safety, security, compliance, clinical,
  performance or commercial results;
- the dependency inventory is incomplete.

`commons-export-lint` implements these checks. It can only check the metadata;
it cannot prove that a recorded review took place.

## 6. Automation boundary

Automation may validate, test, generate manifests, compute digests, check the
index and assemble candidate bundles. Automation must not:

- publish to any package registry (PyPI, npm, container registries or
  marketplaces);
- import anything from a private repository;
- create releases containing private-origin artifacts;
- change a commercial classification.

Public CI uses no repository secrets. Any future workflow that needs
privileged credentials (for example release signing) must use a separate,
explicitly protected trigger and must never run on code from forks.

## 7. Telemetry

Commons tools collect no usage data by default and must work without network
access to any Miskatonic service. Public signals such as stars, forks, issues
and contributions may be observed, but they are not evidence of willingness to
pay, profitability or scientific validity.

## 8. Current state

As of v0.1 no artifact from any private Miskatonic project has been cleared
or released. The only released package is the Commons-native
`commons-export-lint`. Each future export needs its own specific clearance.
