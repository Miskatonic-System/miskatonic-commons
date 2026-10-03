# Provenance records

| File | What it records |
| --- | --- |
| `BOOTSTRAP_REPOSITORY_CREATION_RECEIPT_V0_1.json` | How and when this repository was created |
| `BOOTSTRAP_CLEAN_HISTORY_RECEIPT_V0_1.json` | The single clean root commit and the absence of imported history |
| `COMMONS_00A_CROSS_REPO_CLOSURE_V0_1.json` | Cross-repository closure of the bootstrap. **Corrected by** `COMMONS_00A_CROSS_REPO_CLOSURE_V0_1.ERRATUM_00C.json` (`/temporal_note`) |
| `COMMONS_00A_CROSS_REPO_CLOSURE_V0_1.ERRATUM_00C.json` | Erratum bound by SHA-256 to the unmodified closure receipt |
| `COMMONS_PUBLICATION_FENCE_RECEIPT_V0_1.json` | Provider readback of the `main` publication fence and the adversarial control results |

Records are never edited to change what they said. Corrections are separate,
bound errata.
