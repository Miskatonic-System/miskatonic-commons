# Maintenance Policy (v0.1)

## Maintenance level

Packages are maintained on a **best-effort** basis. Each package's support
class is recorded in its manifest and in the package index:

| Support class | Meaning |
| --- | --- |
| `COMMUNITY_BEST_EFFORT` | Maintainers review issues and pull requests when they can. No schedule or response time is promised. |
| `REFERENCE_NO_MAINTENANCE` | Published as a reference; changes are not expected. |

## Versions

- Packages use semantic versioning (`MAJOR.MINOR.PATCH`).
- Every release is bound to a bundle digest. Changing any file in a released
  bundle requires a new version with a new manifest and clearance receipt.
- Earlier release metadata stays in `releases/` as a record.

## Status changes

An index entry may move from `ACTIVE` to `DEPRECATED` or `WITHDRAWN`.
Withdrawal is recorded, not erased. A withdrawn package should not be used for
new work.

## Public history

Public history is not rewritten for appearance. Rewriting is reserved for
removing material that must not be public (for example an exposed secret), and
even then the secret must be treated as compromised and rotated.

## Dependencies

Runtime dependencies are kept to a minimum and documented in each manifest.
Development dependencies are pinned with hashes in `requirements-dev.txt`.
Third-party GitHub Actions are pinned to full commit SHAs.

## Relationship to private projects

Commons maintainers do not maintain private Miskatonic projects through
Commons, and Commons changes do not flow back into them automatically.
