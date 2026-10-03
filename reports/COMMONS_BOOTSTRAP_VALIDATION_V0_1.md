# Commons Bootstrap Validation (v0.1)

Work order: WO-COMMONS-BOOTSTRAP-00A
Scope: Commons-native bootstrap only. No private software is exported.

## 1. Repository creation and clean history

| Check | Result |
| --- | --- |
| Repository | `Miskatonic-System/miskatonic-commons`, public, created 2026-10-03T16:56:06Z by `gh repo create`. No personal-namespace fallback was used. |
| Root commit | `9e27f1a5e8076d7985d95e9c7e5bcca2f551b9de`, 0 parents, GitHub-generated, contains only `LICENSE` (blob `261eeb9e`). |
| Roots reachable | Exactly one (`git rev-list --max-parents=0 --all`). |
| Submodules, grafts, replace refs | None. |
| Branches / tags at creation | `main` / none. |
| History rewriting | None. The root commit GitHub created was kept as-is. |

Receipts: [`provenance/BOOTSTRAP_REPOSITORY_CREATION_RECEIPT_V0_1.json`](../provenance/BOOTSTRAP_REPOSITORY_CREATION_RECEIPT_V0_1.json),
[`provenance/BOOTSTRAP_CLEAN_HISTORY_RECEIPT_V0_1.json`](../provenance/BOOTSTRAP_CLEAN_HISTORY_RECEIPT_V0_1.json).

Note: GitHub generated the root commit and stamped it with the creating
account's personal email address as author and committer. That address is
therefore public in this repository's history. It is not designated as a
contact anywhere in Commons, and per the work order the commit was not
rewritten. Every later commit uses a GitHub `noreply` address.

## 2. Local validation

Environment: Linux (WSL2), Python 3.14.7, dependencies installed with
`pip install --require-hashes -r requirements-dev.txt` into a fresh virtual
environment.

| Command | Result |
| --- | --- |
| `python -m pytest` | 191 passed, 0 skipped (after review round 1; 127 at round 0) |
| `python scripts/check_sensitive_data.py` | 0 findings |
| `commons_export_lint.py check-index --index releases/package-index-v0.1.json --repo-root .` | OK: no findings |
| `commons_export_lint.py replay-fixtures fixtures --expected fixtures/expected-results.json` | identical |
| `commons_export_lint.py canonicalize $(git ls-files '*.json')` | all canonical |
| `scripts/build_release_metadata.py --check` | release metadata reproducible |
| gitleaks 8.30.1 (`gitleaks git --config .gitleaks.toml --redact --exit-code 1 .`), linux_x64 archive sha256 `551f6fc8…f2470eb` verified | no leaks found |

Absence of scanner findings is not proof that no secret exists.

## 3. Hosted CI (GitHub Actions, PR #1)

Round-0 run `37139457380` on commit `d1065d5f`. The round-1 candidate's run is
recorded on PR #1 and in the post-merge receipt.

| Job | Result |
| --- | --- |
| tests (python 3.12) | pass, 127 passed |
| tests (python 3.13) | pass, 127 passed |
| tests (python 3.14) | pass, 127 passed |
| secret scan (gitleaks 8.30.1, full history) | pass |
| dependency review (dependency-review-action v5.0.0) | first attempt failed: the dependency graph was disabled on the new repository. After enabling vulnerability alerts (which enables the dependency graph), it passed on rerun. |

CI uses no repository secrets (none exist), `permissions: contents: read`,
`persist-credentials: false`, no `pull_request_target`, and actions pinned to
full commit SHAs. It therefore behaves the same for forks.

## 4. Fixture outcomes

Expected codes are declared in `scripts/generate_fixtures.py` by intent. Replay
matches them exactly.

| Fixture | Work-order item | Codes |
| --- | --- | --- |
| VALID-01 Commons-native P3, NONE | VALID-01 | none |
| VALID-02 public source, COMPLEMENTARY, P4, moat recorded | (extra) | none |
| INVALID-01 missing clearance receipt | INVALID-01 | MISSING_CLEARANCE_RECEIPT |
| INVALID-02 UNCERTAIN commercial impact | INVALID-02 | COMMERCIAL_IMPACT_UNRESOLVED |
| INVALID-03 hash mismatch | INVALID-03 | HASH_MISMATCH |
| INVALID-04 opaque origin, leaked remote + commit ID | INVALID-04 | PRIVATE_LOCATOR_LEAK |
| INVALID-05 "scientifically validated" | INVALID-05 | PROHIBITED_CLAIM |
| INVALID-06 unknown release class | INVALID-06 | RELEASE_CLASS_NOT_RELEASABLE, SCHEMA_VIOLATION |
| INVALID-07 dependency without license, inventory incomplete | INVALID-07 | DEPENDENCY_INVENTORY_INCOMPLETE, DEPENDENCY_LICENSE_MISSING, SCHEMA_VIOLATION |
| INVALID-08 undeclared bundle file | INVALID-08 | UNEXPECTED_FILE |
| INVALID-09 not cleared | (T2) | CLEARANCE_NOT_CLEARED |
| INVALID-10 P1 reference-only | (T6) | RELEASE_CLASS_NOT_RELEASABLE |
| INVALID-11 product-market-fit claim | (T9) | PROHIBITED_CLAIM |
| INVALID-12 unknown manifest field | (T10) | SCHEMA_VIOLATION |
| INVALID-13 opaque origin with attribution | (T7) | DISCLOSURE_INCOMPATIBLE |
| INVALID-14 cannibalization risk, no human authorization | (§8) | HUMAN_AUTHORIZATION_MISSING |
| INVALID-15 no retained surface, no strategic review | (§9) | MOAT_REVIEW_MISSING |
| INVALID-16 receipt bound to another bundle | (§25) | RECEIPT_MISMATCH |
| INVALID-17 security dimension pending | (§11) | CLEARANCE_DIMENSION_NOT_PASSED |
| INVALID-18 opaque origin, host path without scheme | review F1 | PRIVATE_LOCATOR_LEAK |
| INVALID-19 opaque origin, short uppercase commit ID | review F1 | PRIVATE_LOCATOR_LEAK |
| INVALID-20 opaque origin, `/tmp` path | review F1 | PRIVATE_LOCATOR_LEAK |
| INVALID-21 opaque origin, private hostname | review F1 | PRIVATE_LOCATOR_LEAK |
| INVALID-22 attributed origin, path outside attribution | review F1 | PRIVATE_LOCATOR_LEAK |
| INVALID-23 personal identity as receipt owner | review F2 | PERSONAL_DATA, SCHEMA_VIOLATION |
| INVALID-24 claim in receipt scope statement | review F3 | PROHIBITED_CLAIM |
| INVALID-25 release ID not bound to package | review F5 | RELEASE_ID_MISMATCH |
| INVALID-26 bundle without license text | review F9 | LICENSE_TEXT_MISSING |
| INDEX-VALID-01 cleared entry | (T11) | none |
| INDEX-INVALID-01 uncleared P2 entry | (T11) | CLEARANCE_NOT_CLEARED, RELEASE_CLASS_NOT_RELEASABLE, SCHEMA_VIOLATION |

## 5. Work-order test map

| Test | Where |
| --- | --- |
| T1 valid native manifest passes | `test_export_lint.py::test_t1_*` (fixture and the real release) |
| T2 non-CLEARED fails | `test_t2_*` (all four non-cleared states, missing receipt, dimension status) |
| T3 hash mismatch fails | `test_t3_*` |
| T4 unknown file fails | `test_t4_*` (also missing file, symlink, unsafe paths) |
| T5 UNCERTAIN fails closed | `test_t5_*` (also high-risk authorization and moat review) |
| T6 P0/P1 release fails | `test_t6_*` (P0, P1, P2) |
| T7 opaque origin rejects locators | `test_t7_*` (19 locator shapes × opaque/native/attributed, receipt, locator fields, attribution) and the review-round-1 tests |
| T8 no scientific authority claims | `test_t8_*` |
| T9 no profitability/PMF claims | `test_t9_*` |
| T10 unknown fields rejected | `test_t10_*` (all schema objects closed; internal validator agrees with `jsonschema` 4.26.0 on 64 documents (61 fixture + 3 real)) |
| T11 index only CLEARED P3/P4 | `test_t11_*` |
| T12 no network | `test_bootstrap_contract.py::test_t12_*` (import allowlist, sockets disabled, isolated `-I` run of the bundle alone) |
| T13 no private repository required | `test_t13_*` (the only organization repository named in tracked files is Commons) |
| T14 deterministic replay | `test_t14_*` (replay, fixture regeneration, release metadata, canonical JSON) |
| T15 Apache-2.0 and notices | `test_t15_*` (LICENSE byte-identical to root commit blob; bundle copies; SPDX headers; hashed pins) |
| T16 no registry publication | `test_t16_*` |
| T17 no telemetry | `test_t17_*` |
| T18 no automatic private back-port | `test_t18_*` |
| T19 no private Git ancestry | `test_t19_*` (requires a full clone; CI uses `fetch-depth: 0`) |
| T20 fresh checkout passes | `test_t20_*` (clone of HEAD, isolated runs) and hosted CI on a fresh runner |

## 6. Mutation check

Run in scratch copies, never in the working tree. Each mutation disabled one
lint rule; the release metadata was regenerated so only behavior changed.

| Disabled rule | Result |
| --- | --- |
| UNCERTAIN fail-closed | killed |
| release-class gate | killed |
| CLEARED gate | killed |
| unexpected-file check | killed |
| file hash check | killed |
| locator scan | killed |
| claim scan | killed |
| `additionalProperties: false` enforcement | killed |
| missing-receipt check | killed |
| human-authorization check | killed |
| dependency-license check | killed |
| index release-class gate | killed |
| clearance-dimension check | killed |
| native private-receipt check | killed |

Round 1 added seven mutations: manifest locator scan, receipt locator scan,
personal-data check, control-character check, release-ID binding,
license-text requirement and receipt claim scan. It also added a widened
`source_attribution` exemption. Two round-0 mutations initially survived the
round-1 suite: the manifest-side CLEARED check (the outcome still failed
through the receipt check) and the native private-receipt check. A targeted
test was added for each.

Round 0: 14 of 14 killed. Round 1: 21 of 21 killed. One real defect was found and fixed during development:
`PurePosixPath` silently normalized `a/./b.txt`, so the unsafe-path check
missed it. The check now splits paths literally.

## 7. Independent review

One fresh-context reviewer looked at the exact round-0 head `dd823070` and
returned **REVISE**, with 2 blocking and 9 non-blocking findings. Repairs were
made inside this work order:

| Finding | Severity | Disposition |
| --- | --- | --- |
| F1 locator scan bypassable (schemeless/host paths, short or uppercase commits, `/tmp` `/etc` `~` and `path:/` forms, internal hosts, receipt `basis`, no scan for attributed origins); docs overstated it | BLOCKING | Repaired. Every manifest and receipt string is scanned at every level; only `source_attribution` and bundle file paths are exempt. Patterns widened, private `--deny-pattern-file` added, 5 fixtures and 19-shape tests added, docs corrected. All the reviewer's blocking probe inputs now fail. |
| F2 personal identity accepted as receipt owner | BLOCKING | Repaired. `owner` and `authority_role` are role tokens `^[a-z][a-z0-9-]{2,63}$`; email, phone and control-character checks run on every string. |
| F3 claim scan covered four fields | non-blocking | Repaired. All manifest and receipt text is scanned except `does_not_establish`; NFKC normalization; "prove(s)" and "demand" wording added. Homoglyphs and adversarial wording remain a limit. |
| F4 opaque IDs could carry private names | non-blocking | Limit. Covered by `--deny-pattern-file` during private review. |
| F5 release ID not bound | non-blocking | Repaired (`RELEASE_ID_MISMATCH`). |
| F6 `imported_at` missing | non-blocking | Repaired. Required manifest field. |
| F7 timestamps predated the repository | non-blocking | Repaired. The real release now records `2026-10-03T17:23:00Z`. Clearance of a Commons-native package is self-attested by Commons maintainers and completed by acceptance of this review. |
| F8 personal email in the GitHub-generated root commit | non-blocking | Recorded plainly in section 1. Not rewritten (work order §32). |
| F9 license text not required in bundle | non-blocking | Repaired (`LICENSE_TEXT_MISSING`). Fixture bundles now ship a LICENSE file. |
| F10 trailing newline accepted by patterns | non-blocking | Repaired (`CONTROL_CHARACTER`). |
| F11 bundle file contents not scanned | non-blocking | Limit. The repository-wide sensitive-data check and gitleaks cover files committed here. |

## 8. Known limits

- The lint checks metadata. It cannot verify that any recorded human review
  happened.
- The claim scan is a fixed phrase list. It catches common upgrades of claims,
  not every possible wording, and it does not map look-alike characters.
- The locator scan matches locator shapes. It cannot recognize the plain name
  of a private project or a relative path that names one. Private reviews
  should use `--deny-pattern-file`.
- The lint does not judge whether a license is suitable (for example,
  proprietary), or what a strategic-review decision actually says.
- `check_sensitive_data.py` and gitleaks are bounded heuristics.
- Dependency review depends on GitHub's dependency graph, which had to be
  enabled on the new repository.
