# Commons Publication Fence 00C (v0.1)

Work order: WO-COMMONS-PUBLICATION-FENCE-00C
Predecessor: WO-COMMONS-INTEGRATION-HARDENING-00B
(`MISKATONIC_COMMONS_CROSS_REPO_INTEGRATION_V0_1_HARDENED`)

Evidence classes used below:

- **[P]** provider-observed fact read back from GitHub;
- **[T]** a result of this repository's test suite;
- **[A]** a policy assertion.

## 1. Starting state [P]

- `main` was at `3cbda3b376f8bc3ce6f18971b405d41f1719c461`, matching the
  frozen value.
- `main` was unprotected, with no repository rulesets and no effective branch
  rules.

## 2. Stage A — provider fence [P]

Ruleset `24431688`, `commons-main-publication-fence-v0.1`, is active and
targets `refs/heads/main`. It has no bypass actors, and the provider reports
`current_user_can_bypass = never` for the administrator account. Its rules:

- deletion is blocked;
- non-fast-forward updates are blocked;
- a pull request is required, with the rebase merge method only;
- five required status checks, in strict mode, all bound to the GitHub Actions
  app (`integration_id` 15368):
  - `tests (python 3.12)`
  - `tests (python 3.13)`
  - `tests (python 3.14)`
  - `secret scan (gitleaks, full history)`
  - `dependency review`

The effective rules reported for `main` come only from this ruleset, and the
branch now reports `protected = true`.

Bypass classification: **PROVIDER_PUBLICATION_FENCE_ENFORCED**. Administrators
can still edit or delete the ruleset itself (see §8).

The full readback is in
[`provenance/COMMONS_PUBLICATION_FENCE_RECEIPT_V0_1.json`](../provenance/COMMONS_PUBLICATION_FENCE_RECEIPT_V0_1.json).

## 3. Stage B — adversarial controls [P]

All merge attempts used
`msk-gh pr merge --expected-head <sha> --method rebase`.

| Control | PR | Observation | Result |
| --- | --- | --- | --- |
| B1 failed check | #3 | Three test checks failed. The provider refused the merge (`GH_CHECKS_NOT_SATISFIED`) and the PR is `blocked`. | MERGE_BLOCKED_REQUIRED_CHECK_FAILED |
| B2 pending check | #4 | Merge attempted while 0 check-runs had reported. The provider refused it (`GH_CHECKS_NOT_SATISFIED`) and the PR is `blocked`. | MERGE_BLOCKED_REQUIRED_CHECK_PENDING |
| B3 head mutation | #6 | Head A went fully green, then head B was pushed. The provider refused the merge of B (`GH_CHECKS_NOT_SATISFIED`), and the PR stayed `blocked` while A's checks were still `success`. An attempt naming A was refused by msk-gh's expected-head guard. | STALE_HEAD_SUCCESS_NOT_ACCEPTED |
| B4 missing check | #5 | The required check was renamed, so `dependency review` was absent while the other five reported checks were green. The provider refused the merge (`GH_CHECKS_NOT_SATISFIED`) and the PR is `blocked`. | MERGE_BLOCKED_REQUIRED_CHECK_MISSING |
| B5 readback | — | The ruleset and the effective rules for `main` read back as configured. | PASS |

All four control PRs were closed without merge, and their branches were
deleted. `main` did not move. No direct push to `main` was attempted.

## 4. Stage D — commit identity spoofing [T]

The identity test no longer reads commit subjects. A commit is exempt as CI's
synthetic pull-request merge only when both of these hold:

- its SHA equals the `GITHUB_SHA` of a `pull_request` event;
- its second parent equals the event payload's `pull_request.head.sha`.

A real merge by a personal identity whose subject mimics `Merge <sha> into
<sha>` is rejected:

- in a push context;
- when it is not the declared merge SHA;
- when its second parent is not the declared PR head.

Result: **SYNTHETIC_MERGE_SUBJECT_SPOOF_REJECTED**. A true synthetic structure
is still exempt.

## 5. Stage E — history-rewrite authority [T]

The phrase heuristic from 00B is replaced by a bounded normative registry,
[`docs/history-norms.v0.1.json`](../docs/history-norms.v0.1.json):

- Every heading, sentence, list item, table row or code line in any normative
  document (root `*.md` and `docs/*.md`) that mentions a history-changing
  action must match a registered clause exactly.
- Every clause must be `PROHIBITED`, carry exactly one negation, and contain no
  permissive or exception wording.

Hostile controls that are rejected:

- explicit force-push permission;
- double negation;
- rewrite permission in another section;
- in a different document;
- in a list item, table row or code block;
- an exception for the bootstrap history;
- registering a permissive, double-negated or contradictory clause;
- deleting a registered prohibition;
- detaching a list item from its prohibiting lead-in.

**Defect found in 00B's claim.** `docs/MAINTENANCE_POLICY.md` contained an
exception granting rewrite authority: "Rewriting is reserved for removing
material that must not be public (for example an exposed secret)". It
contradicted the `PUBLIC_HISTORY_REWRITE_AUTHORITY = NONE` recorded in 00B. The
00B test only scanned the identity policy, so it missed this. The clause is
replaced: an exposed secret is treated as compromised and rotated, and history
is never rewritten. The new checker flags the pre-00C text.

Result: **PUBLIC_HISTORY_REWRITE_AUTHORITY = NONE**, now verified across all
normative documents.

## 6. Stage F — receipt wording [T]

The 00B receipt's `temporal_note` overstated its timing. It is corrected by
[`provenance/COMMONS_00A_CROSS_REPO_CLOSURE_V0_1.ERRATUM_00C.json`](../provenance/COMMONS_00A_CROSS_REPO_CLOSURE_V0_1.ERRATUM_00C.json),
which is bound to the unmodified receipt's SHA-256 and JSON pointer. The
timestamp test now checks the commit that introduced the recorded value, not
the last commit that touched the file. The chronology is unchanged.

## 7. Identity and exports [P]/[A]

- `ACCOUNT_EMAIL_PRIVACY_STATE = HUMAN_ATTESTATION_REQUIRED`. The token cannot
  read the setting, and no attempt was made to change it.
- Merges use the rebase method, which keeps commit authors (noreply) and uses
  GitHub's noreply identity as committer. The merge topology becomes linear,
  as justified by WO §4.
- New personal-email exposure: 0 for the control commits and for this
  candidate's commits. The post-merge state is recorded in the registry
  completion.
- Private-origin export count: 0.

## 8. What 00C does not establish

00C does not establish:

- that any private artifact has been cleared for public release or exported;
- that all private repositories have provider-level branch protection;
- that privileged repository ownership can be made incapable of changing
  provider configuration;
- that Commons has product-market demand or commercial authority;
- that any scientific result gains new evidentiary authority;
- that the historical personal-email exposure has been erased.
