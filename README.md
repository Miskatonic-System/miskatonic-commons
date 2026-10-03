# Miskatonic Commons

Miskatonic Commons is the public, open-source home for small tools, schemas
and reference implementations from Miskatonic Systems that have been cleared
for anyone to use for free.

## What Commons is

- A public repository of **independently usable** artifacts. Each one should
  work on its own, without a Miskatonic account, private service or internal
  infrastructure.
- A **governed distribution surface**. Every artifact listed in
  [`releases/package-index-v0.1.json`](releases/package-index-v0.1.json) has a
  public release manifest and a public clearance receipt describing the bounded
  review it passed before release.
- Licensed under the **Apache License 2.0** unless a specific release says
  otherwise.

## What Commons is not

- **Not everything Miskatonic builds.** Most Miskatonic work is not open
  source. Nothing becomes public by default; each artifact is reviewed and
  released individually.
- **Not a product or a support contract.** Inclusion here does not imply
  product support, an SLA, a warranty or production readiness. See
  [docs/SUPPORT.md](docs/SUPPORT.md).
- **Not a source of scientific evidence.** Commons is not the canonical record
  of any research result. A public release shows only that an artifact was
  cleared for distribution under its recorded scope. It does not make the
  artifact's scientific, safety, security, compliance or performance claims
  stronger than they were.

## What is here today

The repository currently contains its own bootstrap only:

| Path | Contents |
| --- | --- |
| [`tools/commons-export-lint/`](tools/commons-export-lint/) | A standard-library Python tool that validates release manifests, clearance receipts, bundles and the package index. Written directly in Commons; no private code. |
| [`schemas/`](schemas/) | JSON Schemas for release manifests, clearance receipts and the package index (v0.1). |
| [`fixtures/`](fixtures/) | Synthetic valid and invalid release examples used by the tests. |
| [`releases/`](releases/) | The package index and the release metadata for each listed package. |
| [`docs/`](docs/) | Export, provenance, classification, maintenance and support policies. |

No existing private Miskatonic software has been released here yet.

## Using a tool

```sh
git clone https://github.com/Miskatonic-System/miskatonic-commons
cd miskatonic-commons
python tools/commons-export-lint/commons_export_lint.py check-index \
    --index releases/package-index-v0.1.json --repo-root .
```

Running the test suite:

```sh
python -m pip install --require-hashes -r requirements-dev.txt
PYTHONDONTWRITEBYTECODE=1 python -m pytest
```

## How releases work

Artifacts move one way: from an originating project, through an explicit
export review, into a clean public package here. Public history is new; no
private Git history is ever carried into this repository. Read
[docs/EXPORT_POLICY.md](docs/EXPORT_POLICY.md) and
[docs/PROVENANCE_MODEL.md](docs/PROVENANCE_MODEL.md) for the details.

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md)
and the [Code of Conduct](CODE_OF_CONDUCT.md). Contributions improve Commons
itself; they are not automatically copied into any private Miskatonic project.

## Security

Please do not report security problems in public issues. See
[SECURITY.md](SECURITY.md).

## Names and logos

The source-code license does not grant permission to use the Miskatonic name
or logos in a way that suggests official endorsement of your project or
product. Describing where code came from is fine.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
