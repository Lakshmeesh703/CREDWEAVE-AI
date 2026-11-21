# CREDWEAVE AI Data Dictionary

All records created by the Prompt 02 seed are synthetic, use INR, and have stable UUIDs derived from fixture keys. This dictionary describes storage fields; it does not infer risk or evidence quality.

| Table | Purpose | Important constraints |
|---|---|---|
| `businesses` | Merchant identity and consent | Operating months non-negative; consent is `granted`, `pending`, or `withdrawn` |
| `data_sources` | Provenance for an imported or simulated source | `synthetic` is explicit; `(business_id, file_hash)` is unique |
| `transactions` | Normalized money movement | `amount_inr` is `NUMERIC(14,2)`; `(business_id, source_id, external_ref)` is unique |
| `invoices` | Receivable/payable invoice records | `total_inr` is `NUMERIC(14,2)`; invoice number is unique per business |
| `payment_links` | Candidate relationship between an invoice and transaction | Invoice/transaction pair is unique; match status is not a truth claim |
| `counterparties` | Masked customers and suppliers | Identifier is masked and unique per business |
| `obligations` | Monthly obligations | Amount is `NUMERIC(14,2)` |
| `assessments` | Future assessment snapshots | Rule version, status, snapshot, and limitations are retained |
| `reviews` | Human lender review metadata | Reviewer is an alias/name; no automated approval field exists |

## Enumerations

- Consent: `granted`, `pending`, `withdrawn`
- Source kind: `bank`, `upi`, `invoice`, `manual`
- Transaction direction: `credit`, `debit`
- Payment channel: `bank_transfer`, `upi`, `cash`
- Invoice direction: `receivable`, `payable`
- Invoice status: `open`, `paid`, `partial`, `overdue`
- Counterparty type: `customer`, `supplier`, `other`
- Match method: `exact_reference`, `amount_date`, `manual`
- Match status: `matched`, `partial`, `unmatched`, `disputed`
- Review status: `not_started`, `in_review`, `completed`

## Schema and migration strategy

The configured runtime database is Supabase PostgreSQL via `DATABASE_URL`. Prompt 02
uses SQLAlchemy metadata `create_all` for the initial schema. The seed command is
idempotent by clearing the current synthetic dataset and recreating stable fixture
rows. Before production or shared environments, replace `create_all` with versioned
Alembic migrations and scoped tenant authorization.

The fixture intentionally contains duplicate candidates, unmatched records, and supplier concentration inputs as raw facts. Later analytics engines must derive their interpretations rather than storing conclusions in these tables.
