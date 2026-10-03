# Security Policy

## Reporting a vulnerability

Please report security problems privately using GitHub's
**private vulnerability reporting** for this repository:

1. Open the repository's **Security** tab.
2. Choose **Report a vulnerability**.

Do not open a public issue, pull request or discussion for a suspected
vulnerability.

**Never paste an active secret** (password, token, private key, credential)
into any issue, pull request or report, public or private. If you find an
exposed secret in this repository, report its location only; do not copy the
value.

## What to expect

Reports are handled on a best-effort basis by the maintainers. There is no
guaranteed response time and no bug bounty. We will try to acknowledge a
report, discuss a fix privately, and credit reporters who want credit.

## Scope

In scope:

- the code, schemas, workflows and release metadata in this repository;
- release metadata that exposes private information it should not (for
  example a private source location in a release marked as opaque).

Out of scope:

- software that is not in this repository;
- Miskatonic systems or services outside this repository.

## No security certification

The tools here are small utilities offered as-is under the Apache License 2.0.
Nothing in this repository has been certified for production or security
use, and passing its checks is not evidence that an artifact is secure.
Automated secret scanning reduces risk but cannot prove that no secret exists.
