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
| Linear merge method only | Commits keep their own author. The committer is GitHub's noreply identity, so merging never adds a maintainer's personal address. The ruleset's exact allowed method is recorded in the receipt. |
| Non-fast-forward blocked | Force pushes to `main` are not accepted. |
| Deletion blocked | `main` cannot be deleted. |
| Bypass actors | None. GitHub reports that the administrator account cannot bypass the rules. |

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

## Evidence

[`provenance/COMMONS_PUBLICATION_FENCE_RECEIPT_V0_1.json`](../provenance/COMMONS_PUBLICATION_FENCE_RECEIPT_V0_1.json)
holds the following:

- the provider readback of the ruleset and of the effective rules for `main`;
- the required-check identities;
- the outcomes of the adversarial controls: failed, pending, stale-head and
  missing checks were each blocked, and the control pull requests were closed
  without merge.

## Limits

- Repository and organization administrators can still edit or remove the
  ruleset. That is a configuration change visible in GitHub's audit trail, not
  a way to merge around the rules. Nothing here makes privileged ownership
  incapable of changing provider configuration.
- The fence protects this public repository only. It says nothing about other
  repositories.
