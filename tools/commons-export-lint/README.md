# commons-export-lint

A small, dependency-free command-line tool that checks Miskatonic Commons
public release metadata before anything is published.

It validates:

- release manifests, clearance receipts and the package index against the
  Commons v0.1 JSON schemas (unknown fields are rejected);
- that every file in a release bundle is declared, and every declared file is
  present with the recorded SHA-256 hash and size;
- the bundle digest (`commons.bundle-digest.v0.1`, see below);
- that only `CLEARED` releases of class `P3` or `P4` can be released or indexed;
- that commercial impact `UNCERTAIN` fails closed, and that the higher-risk
  commercial classes carry a recorded review and authorization;
- that opaque or Commons-native releases contain no source locators
  (URLs, remotes, commit IDs, absolute paths);
- that release text does not claim scientific, safety, security, compliance,
  clinical, performance or commercial results;
- that dependency and license declarations are complete;
- that JSON files use the one canonical serialization.

It is a lint, not an authority. A clean result means the metadata is complete
and consistent under these rules. It does not mean the software is correct,
safe or useful, and the tool cannot confirm that any review recorded in a
receipt really happened.

## Requirements

Python 3.10 or newer. No third-party packages, no network access, no account.

## Usage

```sh
python commons_export_lint.py check-release \
    --manifest path/to/manifest.json \
    --receipt path/to/clearance-receipt.json \
    --bundle-root path/to/bundle/

python commons_export_lint.py check-index \
    --index releases/package-index-v0.1.json --repo-root .

python commons_export_lint.py describe-bundle path/to/bundle/
python commons_export_lint.py replay-fixtures fixtures/ --expected fixtures/expected-results.json
python commons_export_lint.py canonicalize --write some.json
```

Add `--json` to `check-release` or `check-index` for machine-readable output.
Exit status is `0` with no findings, `1` with findings and `2` on a usage or
read error.

The schemas bundled in `schemas/` are used by default; pass `--schema-dir` to
use another copy.

### Bundle hygiene

The unexpected-file check has no ignore list. Running Python from inside a
bundle directory can create `__pycache__/` files, which will then be reported.
Set `PYTHONDONTWRITEBYTECODE=1` or remove them before checking.

## Bundle digest

`commons.bundle-digest.v0.1` is the SHA-256 of the UTF-8 text formed by one
line per file, `<sha256-hex><two spaces><relative-path>\n`, sorted by line.
This is the same line format `sha256sum` prints, so it can be reproduced with
ordinary tools.

## Canonical JSON

Canonical form is `json.dumps(obj, indent=2, sort_keys=True,
ensure_ascii=False)` followed by a single newline, encoded as UTF-8 without a
byte-order mark. Duplicate object keys are rejected.

## Privacy

The tool collects nothing and sends nothing. It reads only the files you name
and writes only when you pass `canonicalize --write`.

## License

Apache License 2.0. See `LICENSE` and `NOTICE`.
