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

Public history is never rewritten.
This policy grants **no** authority to rewrite public history for any reason, including to remove an exposed secret.
An exposed secret is treated as compromised and rotated; it is never treated as
hidden. The machine-readable form of this rule is
[`docs/history-norms.v0.1.json`](history-norms.v0.1.json).

## Dependencies

Runtime dependencies are kept to a minimum and documented in each manifest.
Development dependencies are pinned with hashes in `requirements-dev.txt`.
Third-party GitHub Actions are pinned to full commit SHAs.

## Relationship to private projects

Commons maintainers do not maintain private Miskatonic projects through
Commons, and Commons changes do not flow back into them automatically.
