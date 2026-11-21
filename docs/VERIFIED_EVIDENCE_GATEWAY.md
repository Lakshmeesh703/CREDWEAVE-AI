# Verified Evidence Gateway

Open **Verified Evidence Gateway** from a business workspace. Owners and consented lenders can inspect provenance and status history. Owners can run **Compare supporting records**, which reuses the Evidence DNA invoice and receipt matching rules and appends changed results. Earlier Passport snapshots retain the status counts recorded when the assessment was created.

| Status | Meaning |
| --- | --- |
| Unverified | Uploaded or historical data with no independent confirmation |
| Partially supported | An invoice and receipt from distinct uploaded sources align under the configured matching rules |
| Requires review | Validation or reconciliation flagged an inconsistency or missing detail |
| Institutional source verified | Reserved for an authenticated institutional connection. This version does not include a live provider. |
| Simulated source verification | Explicitly synthetic demo fixture. No bank or other institution was contacted. |

CSV validation covers required columns, strict dates, INR amounts, file type, size, duplicate references, and running balances when supplied. Use the existing `amount_inr,direction` columns or replace them with `debit_inr,credit_inr`. Optional columns include `balance_inr` and `source_provider`. Provider names in uploads are assertions made by the uploader. Balances are interpreted as post-transaction values, comparing adjacent rows in ascending or descending date order. Preserve statement order for multiple transactions on the same date. Unusable files are rejected as a unit. Missing descriptions, repeated-transaction candidates, and balance inconsistencies are kept as human review findings. Those flags do not change the existing cash-flow and risk calculations.

Each transaction, invoice, and obligation can have an immutable provenance record. The gateway stores available source metadata and the original file’s SHA-256 digest. It does not retain the raw file or running-balance column. Institutional consent references are reserved for future authenticated connectors. Old obligations lack a direct source link, so their migration leaves it blank. Pre-migration checks cannot be reconstructed from a hash, so historical imports start unverified.

## Apply the PostgreSQL migration

For the intended portal database, run the versioned migration after the existing schema has been initialized. Back up the target first and schedule the backfill when uploads can wait. From the repository root:

```bash
cd backend
set -a
source ../.env
set +a
.venv/bin/python -m app.db.migrate
```

The migration creates and backfills the gateway tables in one transaction, records its version, and enables RLS with direct table grants revoked. The migration takes write-conflicting locks during backfill. Existing PostgreSQL imports continue to work until the migration is applied, then the gateway becomes available immediately. SQLite tests and the jury launcher create their own isolated schema.

The gateway shares the portal’s existing business ownership and lender-consent rules. Raw uploaded files have no public storage URL. A digest identifies a particular file but does not certify its content. Verification results assist human review and do not establish a legal conclusion.
