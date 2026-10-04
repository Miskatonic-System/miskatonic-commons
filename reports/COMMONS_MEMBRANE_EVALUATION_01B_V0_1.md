# First-export membrane evaluation (01B)

Work order: WO-COMMONS-MEMBRANE-EVALUATION-01B
Specimen: the first private-origin export, `algorithm-trace-core` 0.1.0 (WO-COMMONS-FIRST-EXPORT-01A, merged as `f8867885`)

This work order studies how the export membrane behaved on its first use, and repairs the
bounded defects found. It authorizes no second export. The count of private artifacts exported
is **1** before and after.

Fact classes:

- **[S]** private source fact;
- **[R]** publicly reproducible fact;
- **[P]** provider-observed fact;
- **[A]** policy assertion.

## Results

| Item | Result |
| --- | --- |
| Private artifacts exported | 1 before, 1 after |
| Public packages | 2 before, 2 after (both now at 0.1.1) |
| Parity replay reproducible | yes, byte for byte, from fresh checkouts **[S]** |
| Hostile-control mutants, 0.1.0 | 68 raise sites: 29 killed, 39 survived |
| Survivors: semantically equivalent | 2 |
| Survivors: outside the claimed rejection surface | 4 |
| Survivors: redundant mutation | 1 |
| Survivors: test-oracle blind spot | 32 (26 would accept an invalid trace, 6 would raise outside the error envelope) |
| Survivors: actual replay acceptance defect | 0 |
| Acceptance defects found by direct search | 1 in 0.1.0: run-record comparison; repaired in 0.1.1 |
| Hostile-control mutants, 0.1.1 | 69 raise sites: 62 killed, 7 survived (the 2 + 4 + 1 above) |
| Known invalid public-contract input accepted by 0.1.1 | none |
| Origin-name controls | 17 negative, 4 positive |
| Profile-resolution controls | 2 negative, 2 positive |
| Claim-scan SLA controls | 27 negative wordings, 8 exact non-claim statements, 1 structural |
| Disclosure controls | 10 negative, 6 positive, 1 clearance-semantics control |
| Commons fence | `COMMONS_FENCE_MATCHES_EXPECTED` **[P]** |

The full mutation matrix, the control-to-obligation map and the defect search are in
[`COMMONS_HOSTILE_CONTROL_AUDIT_01B_V0_1.json`](COMMONS_HOSTILE_CONTROL_AUDIT_01B_V0_1.json).

## Parity reproducibility [S]

The 0.1.0 parity report was bound only by its digest. A private, deterministic reproduction
recipe is now kept with the private evidence. It records:

- both source commits;
- the working layout and how the normalization table is applied;
- how the public example profile is added to the private catalog;
- the pinned dependencies and the command;
- the expected output digest and the environment assumptions.

Run from fresh clones in a fresh environment, it reproduces the report byte for byte
(`6964f46c…`). The same harness, run against 0.1.1, produces the identical report.

## Normalization-table digest [R]/[A]

The recorded `table_sha256` of 0.1.0 is SHA-256 of `json.dumps(table)` with Python's default
separators. It is not RFC 8785. `PROVENANCE.json` now states this next to the unchanged value.
Future membrane records use SHA-256 of RFC 8785 bytes. No recorded digest was recomputed.

## Maintenance releases [R]

- **`algorithm-trace-core` 0.1.1.** It adds no private source and does not widen the source
  membrane. It is not a second export.
  - Profile-module discovery failures stay in the error envelope as
    `PROFILE_MODULE_RESOLUTION_FAILED`. An exception from the pinned module itself is still not
    rewritten.
  - Run-record fields are compared as JSON (by RFC 8785 bytes). 0.1.0 compared them with Python
    `!=`, under which `true` equals `1`, so it accepted a run record whose result said
    `[2, false, 3, true]` for a trace whose result was `[2, 0, 3, 1]`. The frozen source has the same
    comparison. It is the only acceptance defect found.
  - 41 core-isolating hostile controls, each with a positive twin that must replay cleanly.
  - The README documents the error boundaries and the frame-scope semantics.
- **`commons-export-lint` 0.1.1.**
  - A sentence that mentions an SLA is a claim unless the whole sentence is one of eight exact
    non-claim statements: a plain negation of an offer, a statement about possible future commercial
    service, a reference to the term, or a statement that SLAs are outside the artifact. Added words
    anywhere in the sentence make it a claim again. The schema-fixed moat value is exempt by path.
  - Detection now also covers plural and spelled-out forms.
  - A first, looser design judged each occurrence by its nearby words. It passed affirmative
    wordings that 0.1.0 had rejected. It was replaced before merge, and those wordings are now
    hostile controls.

The 0.1.0 release records stay unchanged in `releases/`.

## Hostile-control independence [R]

Most of the 0.1.0 survivors were checks that the example profile's own hooks, or an earlier
check, made unreachable to the existing controls. They were not acceptance defects: on the
unmutated package, every one of the new invalid traces is rejected with its documented code.

The new controls reach the core directly. Some use a test-only profile whose hooks always
accept, so only the core can reject.

- The 23 original controls exercise 23 distinct obligations.
- The full set of 64 controls exercises 61 distinct obligations.
- Two pairs of controls are deliberate isolation twins. One more pair exercises the run-record
  obligation with two value kinds; one of them pins the 0.1.1 repair.

A frame scope does not restrict which cells its events access. That is a documented boundary,
not a defect.

## Origin-name scope [R]

The origin of a release may now be named only in:

- its `PROVENANCE.json`;
- its release manifests and receipts;
- the exact files listed in
  [`provenance/ORIGIN_DISCLOSURE_LOCATIONS_V0_1.json`](../provenance/ORIGIN_DISCLOSURE_LOCATIONS_V0_1.json).

A file anywhere under `reports/` no longer qualifies.

Text is folded before matching: HTML entities and percent-encoding, case, Unicode dashes, and `\` as `/`. The disclosed name
is matched bare and with any short separator between its parts. The earlier check matched neither.
Names of private repositories that were never disclosed cannot be listed without publishing them,
so they are caught only with the organization prefix.

## Disclosure deviation in 01A [A]

Commit `fe2f49e6`, the first public candidate commit of 01A, carried two kinds of private
material:

- a summary of the private review process: an outcome and a round count;
- an internal commercial-review label.

A short narrative about an earlier draft test was also included. The final 01A head removed all
three. The repository owner then explicitly cleared the summary for disclosure. It stays in
history, consistent with the no-rewrite policy.

**Why nothing blocked it.**

- No check targeted review content. The name check looked only for repository names.
- The claim scan looked only at release metadata, not at reports.

**Why the limited clearance was acceptable.**

- The material was already public on the pull request.
- It contained no secret, personal data or source.
- The owner cleared it explicitly.

**The new control.** `PRIVATE_REVIEW_CONTENT_PUBLICATION_REQUIRES_EXPLICIT_CLEARANCE` is a bounded
marker check over every private-origin release surface and every file under `reports/`, with exact
clearance entries
([`docs/private-review-markers.v0.1.json`](../docs/private-review-markers.v0.1.json)). The 14
clearance entries cover the records of this repository's own public pull-request reviews in the
00A–00C reports. Run
against the content of `fe2f49e6`, it catches the review outcome, the round count and the
commercial label. It does not catch the narrative about the draft test, which uses no marker
wording. Ordinary statements such as "independently reviewed" pass.

## Deviation during 01B [A]

The first version of this work was opened as pull request #11. A hostile test string in two of its
commits named a private organization repository: the string was split so that the repository's own
name check did not see it. Pull request #11 was closed unmerged,
and this version was rebuilt from `main`, so the name never entered `main`. It remains visible in
the closed pull request's commits. Nothing was force-pushed.

Before every public push, the candidate diff is now scanned for every organization repository name,
case-insensitively and with string concatenation removed.

## Workflow integrity [A]

The required checks run the workflow from the pull request's own head. A pull request that edits
`.github/workflows/ci.yml` can therefore weaken what a check runs while keeping its name, and the
check would still report success.

- **Code-owner review.** Requiring a code-owner approval is not proportionate with a single
  maintainer. That maintainer could not approve their own pull request.
- **Bounded repair (made).** The workflow's SHA-256 is now part of the custodied fence state. The
  suite fails if the file differs from it, so a workflow change has to change the custody record
  in the same reviewed pull request. That makes the change visible. It does not prevent it.
- **Prevention.** That needs organization-level controls, such as a required workflow run from a
  protected source. This is recommended as a separate organizational work order.

## Fence configuration custody [P]/[R]

[`provenance/COMMONS_FENCE_EXPECTED_STATE_V0_1.json`](../provenance/COMMONS_FENCE_EXPECTED_STATE_V0_1.json)
records the expected state of ruleset 24431688 and the workflow digest. Its expected-state digest
is `23788d6bdd3e29f7607c4b5ffcf228fb0d6990135acd285bf6bcf19f2a24ae8a` (RFC 8785).
`scripts/audit_commons_fence.py` reports `COMMONS_FENCE_MATCHES_EXPECTED`, `COMMONS_FENCE_DRIFT`
or `COMMONS_FENCE_UNOBSERVABLE`. A deleted ruleset is reported as drift. Fourteen offline drift
controls (thirteen ruleset changes and a deleted ruleset), two workflow controls (changed and deleted)
and three unobservable controls cover it. It detects administrator changes; it cannot prevent them.

## History-rewrite policy [A]

`docs/history-norms.v0.1.json` now carries the authoritative policy as three fields:

- `history_rewrite_authorized: false`;
- `force_push_authorized: false`;
- `rebase_public_history_authorized: false`.

Prose explains these fields, and the clause lint keeps the prose consistent with them. The provider
ruleset enforces them on `main` only. Other branches are not provider-protected, but the policy
still applies to them.

## What this does not establish

- That the membrane is safe in general, or for any other artifact.
- That a second export is authorized or ready. No successor is authorized by this work.
- That mutation survival or kill counts measure correctness. The audit classifies observed
  behavior only.
- That the marker, name and claim checks understand prose. They are bounded pattern checks.
