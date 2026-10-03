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
- a pull request is required, with the merge-commit method only (the first
  configuration allowed only rebase; see §7);
- five required status checks, in strict mode, all bound to the GitHub Actions
  app (`integration_id` 15368):
  - `tests (python 3.12)`
  - `tests (python 3.13)`
  - `tests (python 3.14)`
  - `secret scan (gitleaks, full history)`
  - `dependency review`

The effective rules reported for `main` come only from this ruleset, and the
branch now reports `protected = true`.

Bypass classification: **PROVIDER_PUBLICATION_FENCE_ENFORCED**. No actor can
merge into `main` around the required checks.

An administrator can still edit, disable or delete the ruleset. In particular,
an administrator can disable it, push to `main`, and enable it again. That is a
configuration change, not a merge through the fence. Audit-log entries for it
were not observed by the executor. See §8.

The full readback is in
[`provenance/COMMONS_PUBLICATION_FENCE_RECEIPT_V0_1.json`](../provenance/COMMONS_PUBLICATION_FENCE_RECEIPT_V0_1.json).

## 3. Stage B — adversarial controls [P]

All merge attempts used `msk-gh pr merge --expected-head <sha>`, with the
merge method allowed at the time. B2 and B3 were re-run after review round 0
showed that the first attempts happened before any check-run existed. Those
first attempts showed absent checks rather than pending ones. They are kept in
the receipt as absent-check observations.

| Control | PR | Observation | Result |
| --- | --- | --- | --- |
| B1 failed check | #3 | Three test checks failed. The provider refused the merge (`GH_CHECKS_NOT_SATISFIED`) and the PR is `blocked`. | MERGE_BLOCKED_REQUIRED_CHECK_FAILED |
| B2 pending check | #8 | At 21:40:09Z all 5 required check-runs existed with status `queued`. The provider refused the merge (`GH_CHECKS_NOT_SATISFIED`) and the PR is `blocked`. | MERGE_BLOCKED_REQUIRED_CHECK_PENDING |
| B3 head mutation | #9 | Head A had all 5 checks `success` and the PR was `clean`. Head B was then pushed. At 21:41:09Z, with B's checks `queued` or `in_progress`, the provider refused the merge of B (`GH_CHECKS_NOT_SATISFIED`). The PR stayed `blocked` while A's checks were still `success`. | STALE_HEAD_SUCCESS_NOT_ACCEPTED |
| B4 missing check | #5 | The required check was renamed, so `dependency review` was absent while the other five reported checks were green. The provider refused the merge (`GH_CHECKS_NOT_SATISFIED`) and the PR is `blocked`. | MERGE_BLOCKED_REQUIRED_CHECK_MISSING |
| B5 readback | — | The ruleset and the effective rules for `main` read back as configured. | PASS |

All six control PRs (#3, #4, #5, #6, #8 and #9) were closed without merge, and
their branches were deleted. `main` did not move. No direct push to `main` was attempted.

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

Review round 0 bypassed the first version with ten inputs:

- `git push --force` and `--force-with-lease`;
- "re-writing" and "re-base";
- purging commits with BFG;
- replacing or dropping commits;
- "exempt from the history rule";
- "waive the preceding rule";
- "does not apply to the bootstrap commits";
- a Cyrillic homoglyph.

Version 2 adds:

- expanded action terms;
- a second tier: any unit that combines a history-scope word with permissive
  or exception wording must be registered, either as a `PROHIBITED` clause or
  as a reviewed `ACKNOWLEDGED_NON_HISTORY` statement, and acknowledged
  statements may never name a history-changing action;
- NFKC folding;
- a ban on non-ASCII letters in normative documents;
- `.github/*.md` in scope.

All the reviewer's inputs are now test cases and are rejected, together with:

- explicit force-push permission;
- double negation;
- permission in another section, another document, a list item, a table row
  or a code block;
- a bootstrap exception;
- contradictory or permissive registered clauses;
- deleted prohibitions;
- detached list items.

The check remains bounded and pattern-based. It does not prove the absence of
every possible permissive phrasing.

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

- **Correction.** The first candidate claimed that rebase merges use GitHub's
  noreply identity as committer. Review round 0 showed this to be false with
  public evidence, and the executor confirmed it independently: provider
  merges stamp the merging account's commit email.
- `ACCOUNT_EMAIL_PRIVACY_STATE = HUMAN_ATTESTED_AND_PROVIDER_VERIFIED_BY_PRIVATE_PROBE`.
  - The account holder attested that "Keep my email addresses private" is
    enabled.
  - A private throwaway repository in the maintainer's personal namespace then
    showed the account noreply address for an API commit, for the web
    initialization commit, and as committer of a provider rebase merge.
  - The token cannot read the setting directly, and no attempt was made to
    change it.
- The ruleset now allows only the merge-commit method. That method keeps the
  reviewed head as a parent and keeps the repository's existing topology.
- The identity test checks the committer of every commit on canonical `main`,
  so an exposing merge would fail CI.
- New personal-email exposure: 0 for the control commits and for this
  candidate's commits. The post-merge state is recorded in the registry
  completion.
- Private-origin export count: 0.

## 8. Disclosed limits

- **Workflow tampering.** Required checks are produced by the workflow in the
  pull request's own head. A pull request that edits
  `.github/workflows/ci.yml` can change what the checks execute. The fence
  proves only that GitHub Actions reported success under the required names.
  Workflow changes need independent review before merge.
- **Administrator override.** The administrator disable-push-re-enable path
  described in §2.

## 9. What 00C does not establish

00C does not establish:

- that any private artifact has been cleared for public release or exported;
- that all private repositories have provider-level branch protection;
- that privileged repository ownership can be made incapable of changing
  provider configuration;
- that Commons has product-market demand or commercial authority;
- that any scientific result gains new evidentiary authority;
- that the historical personal-email exposure has been erased.
