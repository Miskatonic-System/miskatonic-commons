# Publication Fence

Since WO-COMMONS-PUBLICATION-FENCE-00C, `main` in this repository is protected
by a GitHub repository ruleset, `commons-main-publication-fence-v0.1`. The
rules are enforced by GitHub. Process and documentation alone do not enforce
them.

## Rules on `main`

| Rule | Effect |
| --- | --- |
| Pull request required | `main` changes only through a merged pull request. Direct pushes are refused. |
| Required status checks (strict) | Every check below must succeed on the pull request's current head, and the branch must be up to date with `main`. Failed, pending or missing checks block the merge. |
| Merge-commit method only | The reviewed pull-request head becomes a parent of the merge commit, unchanged. This keeps the repository's existing merge topology. |
| Non-fast-forward blocked | Force pushes to `main` are not accepted. |
| Deletion blocked | `main` cannot be deleted. |
| Bypass actors | None; GitHub reports `current_user_can_bypass = never` for the administrator account. |

Other pull-request parameters are recorded in the provenance receipt:

- required approving reviews: 0;
- stale reviews dismissed on push;
- no code-owner review;
- no extra approval for unattributed changes.

Required checks, all produced by the GitHub Actions app:

- `tests (python 3.12)`
- `tests (python 3.13)`
- `tests (python 3.14)`
- `secret scan (gitleaks, full history)`
- `dependency review`

If a job is renamed or removed from `.github/workflows/ci.yml`, the ruleset
must be updated in the same change, or every pull request stays blocked. The
test `tests/test_publication_fence.py` fails when the workflow and the
recorded required checks drift apart.

## Merge identity

A provider merge stamps the merging account's commit email onto the merge
commit. That email is the private GitHub noreply address only when the
account's "Keep my email addresses private" setting is on.

For this repository's maintainer account:

- The setting was attested by the account holder on 2026-10-03.
- It was confirmed the same day by a provider merge in a private throwaway
  repository, which produced a noreply committer.
- The identity test checks every committer on canonical history, so a merge
  that exposed an address would fail CI.

## Evidence

[`provenance/COMMONS_PUBLICATION_FENCE_RECEIPT_V0_1.json`](../provenance/COMMONS_PUBLICATION_FENCE_RECEIPT_V0_1.json)
holds the following:

- the provider readback of the ruleset and of the effective rules for `main`;
- the required-check identities;
- the outcomes of the adversarial controls.

## Limits

- An administrator can still edit, disable or delete the ruleset. Disabling
  it, pushing to `main` and enabling it again is possible. That is a
  configuration change, not a merge through the fence. Nothing here makes
  privileged ownership incapable of changing provider configuration.
- Required checks are produced by the workflow in the pull request's own head.
  A pull request that edits `.github/workflows/ci.yml` can change what those
  checks run. The fence proves that GitHub Actions reported success under the
  required names, not what the checks executed. Changes to workflows therefore
  need independent review before merge.
- The fence protects this public repository only. It says nothing about other
  repositories.
