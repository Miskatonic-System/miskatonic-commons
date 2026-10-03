# Provenance Model (v0.1)

Commons keeps two separate provenance records for each export. Only one of
them is public.

## Private clearance receipt

Held by the originating project, never published unless separately cleared.
It records the full evidence for the export decision, for example:

- the exact originating project and source revision;
- the exact source paths and source artifact hashes;
- references to the origin's own results and claim boundaries;
- security, secret, dependency, third-party license and commercial-impact
  reviews;
- the export decision and who made it;
- the approved public bytes or bundle digest.

## Public clearance receipt

Published in Commons as `clearance-receipt.json`
([schema](../schemas/public-clearance-receipt-v0.1.schema.json)). It contains
only public-safe facts:

- an opaque `clearance_receipt_id` (never a repository name, path or commit);
- the release identity: `public_release_id`, `package_id`, `version`;
- the bound `bundle_sha256`;
- `release_class`, `commercial_impact`, `source_disclosure_level`;
- `clearance_status` and `completed_at`;
- a `scope_statement` saying what was cleared;
- the status, owning role and basis of each clearance dimension;
- whether a private receipt exists (`HELD_PRIVATELY` with an opaque reference,
  or `NOT_APPLICABLE_COMMONS_NATIVE`);
- the minimum-viable-moat review and human authorization, where required;
- acknowledgement of the Apache-2.0 patent grant, where applicable.

Reviewers are recorded by role, not by personal identity.

The matching `manifest.json`
([schema](../schemas/public-release-manifest-v0.1.schema.json)) adds the file
list and hashes, license, notices, dependency inventory, support class, public
claim boundary and `approved_at`.

The public record never needs to reveal a private origin's identity. This
keeps provenance infrastructure from exposing private organizational
structure.

## Source disclosure levels

| Level | Meaning | `source_attribution` |
| --- | --- | --- |
| `PUBLIC_SOURCE` | The origin is already public and may be cited. | Required |
| `PUBLIC_ATTRIBUTED_PRIVATE_ORIGIN` | The origin is private, but naming it has been approved. | Required |
| `PRIVATE_ORIGIN_OPAQUE` | The origin stays internal; only the opaque receipt ID and public claim statement appear. | Forbidden |
| `COMMONS_NATIVE` | Written directly in Commons; no private ancestry. | Forbidden |

At **every** level, source locators may appear only inside an approved
`source_attribution` block. `commons-export-lint` scans all other manifest and
receipt text for locator shapes and rejects:

- URLs with a scheme, and host-plus-path forms without one
  (`example.org/group/repo`);
- `user@host:path` Git remotes and `<organization>/<repository>` references
  to this organization's other repositories;
- commit IDs of 7 to 40 hexadecimal characters, in either case;
- absolute paths (`/…`, `~/…`, Windows drive and UNC paths);
- private hostnames (`*.internal`, `*.corp`, `*.lan`, `*.local`, `localhost`)
  and private IPv4 addresses.

It also rejects email addresses, phone numbers and control characters
anywhere, and requires reviewer and authority fields to be role tokens such as
`commons-maintainers`.

This is a **bounded pattern scan**. It cannot recognize the plain name of a
private project. A private export review should pass its own list of private
names with `--deny-pattern-file` (the list itself stays private) and still
read the metadata by hand.

## Clearance states

`NOT_REVIEWED`, `REVIEW_IN_PROGRESS`, `CLEARED`, `REJECTED`, `SUPERSEDED`.
Only `CLEARED` releases may be released or appear in the package index.

## Bundle digest

`commons.bundle-digest.v0.1`: SHA-256 over the lines
`<sha256>  <path>\n` (one per file, sorted). The manifest, receipt and
index all bind to this digest.

## Repository provenance

[`provenance/`](../provenance/) holds the receipts for the creation of this
repository and the evidence that its history starts from a clean public root
with no imported private parents.
