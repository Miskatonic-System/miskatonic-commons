# Contributing to Miskatonic Commons

Thank you for helping. Issues and pull requests are welcome from anyone.

## Before you start

- For a bug, open an issue using the bug report template.
- For a larger change, open an issue first so it can be discussed.
- For a security problem, follow [SECURITY.md](SECURITY.md) instead.

## Making a change

1. Fork the repository and create a branch.
2. Install the pinned development dependencies:

   ```sh
   python -m pip install --require-hashes -r requirements-dev.txt
   ```

3. Run the checks that CI runs:

   ```sh
   export PYTHONDONTWRITEBYTECODE=1
   python scripts/check_sensitive_data.py
   python tools/commons-export-lint/commons_export_lint.py check-index \
       --index releases/package-index-v0.1.json --repo-root .
   python -m pytest
   ```

4. Open a pull request and fill in the template.

CI needs no secrets and no private access, so it runs the same way on forks.

## Changes to a released tool

Released bundles are hash-pinned. If you change a file inside a released
bundle (for example `tools/commons-export-lint/`), the release manifest no
longer matches and CI will fail. That is intended: maintainers handle new
versions and their release metadata. You do not need to update manifests in
your pull request; say in the description that a bundle changed.

## Rules for every contribution

- **License.** By contributing you agree your contribution is licensed under
  the Apache License 2.0, as described in section 5 of the license. There is
  no separate contributor license agreement.
- **Only your own work, or work you may relicense.** Do not submit code you
  are not entitled to contribute under Apache-2.0. Record any new third-party
  dependency and its license.
- **No secrets, no private material.** Never commit credentials, keys,
  environment files, private endpoints, or content copied from private
  repositories.
- **No telemetry.** Tools here must work without collecting usage data and
  must not phone home.
- **Bounded claims.** Documentation and metadata must not claim scientific,
  safety, security, compliance, clinical, performance or commercial results.

## What a merged contribution does and does not do

A merged pull request changes Commons. It does **not** automatically change
any private Miskatonic project, research record or result. If an improvement
is useful to a private originating project, that project's own maintainers
decide independently whether and how to adopt it, through their normal
review. There is no automatic back-port.

## Conduct

Everyone taking part is expected to follow the
[Code of Conduct](CODE_OF_CONDUCT.md).
