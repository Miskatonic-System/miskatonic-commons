# Public Release Classes (v0.1)

Every export candidate carries exactly one release class. A class applies to
one specific candidate or bundle. It never applies automatically to the whole
project the candidate came from.

| Class | Meaning | May be released / indexed |
| --- | --- | --- |
| `P0_INTERNAL_ONLY` | Public distribution prohibited. | No |
| `P1_REFERENCE_ONLY` | May be discussed or documented publicly; no distributable implementation is cleared. | No |
| `P2_PUBLIC_UTILITY_CANDIDATE` | Candidate undergoing clearance. | No |
| `P3_PUBLIC_RELEASE_APPROVED` | Approved for the specifically bound public release bundle. | Yes |
| `P4_PUBLIC_STRATEGIC_OPEN_SOURCE` | Public availability is itself an intentional organizational strategy. | Yes |

Rules:

- Only `P3` and `P4` releases with clearance state `CLEARED` may enter the
  package index. The index schema and `commons-export-lint` both enforce this.
- A `P3`/`P4` class is bound to one bundle digest. A new version needs its own
  manifest, receipt and class.
- Release class is independent of commercial impact (see
  [COMMERCIAL_IMPACT.md](COMMERCIAL_IMPACT.md)). A `P3` artifact can still be
  blocked by an `UNCERTAIN` commercial impact.
- A release class says nothing about whether an artifact is scientifically
  valid, safe or fit for any purpose.
