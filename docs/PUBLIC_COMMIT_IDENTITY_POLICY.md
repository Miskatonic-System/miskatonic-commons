# Public Commit Identity Policy

Commit metadata in this repository is public, permanent and widely mirrored.
This policy prevents automated or maintainer tooling from leaking a personal
email address by accident.

## Rule for automated and maintainer-operated commits

Commits created by automation, scripts, AI coding assistants, or maintainers
operating merge tooling on canonical `main` **should** use one of:

- a GitHub `noreply` identity (`<id>+<login>@users.noreply.github.com`), or
- an organization-safe public identity that is intentionally published.

This applies to the author **and** the committer, and includes merge commits.
GitHub's web and API merge buttons stamp a merge commit with the merging
account's commit email. Since WO-COMMONS-PUBLICATION-FENCE-00C, `main` is
behind a provider ruleset that only accepts pull requests merged with the
provider's linear merge method. That method keeps each commit's own author and
uses GitHub's noreply identity as committer, so it cannot add the merging
account's address. See [docs/PUBLICATION_FENCE.md](PUBLICATION_FENCE.md).

The repository test `test_maintainer_merges_and_automation_commits_use_safe_identity`
checks merge commits and commits that carry an automation trailer. CI's
synthetic pull-request merge is recognized from the GitHub event payload, not
from its commit subject.

## Contributors

This rule does **not** require anyone to hide an identity they choose to
publish. External contributors may sign their own commits with any address
they are comfortable making public. The rule exists to stop accidental leakage
by tooling, not to anonymize voluntary contributors.

## History is not rewritten

This policy applies to new commits only. It grants **no** authority to rewrite,
filter, rebase or force-push public history. Two historical commits expose a
personal address: the GitHub-generated root commit and the bootstrap merge
commit. They are recorded in
[`provenance/COMMONS_00A_CROSS_REPO_CLOSURE_V0_1.json`](../provenance/COMMONS_00A_CROSS_REPO_CLOSURE_V0_1.json)
without repeating the address, and they remain unchanged.
