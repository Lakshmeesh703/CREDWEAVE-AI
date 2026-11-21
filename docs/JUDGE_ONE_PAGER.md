# CREDWEAVE AI — judge one-pager

## Finance F2: Credit for the Credit-Invisible

Small businesses may have meaningful operating activity but fragmented formal records. CREDWEAVE AI turns sample records into a source-linked review workflow for a human lender—without presenting missing data as misconduct or claiming an automated credit decision.

## Four demo moments

### 1. Evidence DNA — consistency is not authenticity

Displays completeness, consistency, categorical verification counts, and assessment confidence separately. A lender can follow a reported revenue claim into source records and see which checks were performed. Cross-source alignment only establishes that selected records agree; it does not prove a transaction is genuine.

### 2. Trust Graph — inspect relationships and gaps

Uses NetworkX to link the business, counterparties, invoices, and transactions with provenance. Duplicate candidates, unmatched records, and supplier concentration are transparent review prompts. They are never presented as proven fraud.

### 3. CashFlow Twin — explore disclosed scenarios

Applies deterministic revenue/expense shocks and a simplified payment-delay model to observed monthly data. It reveals month-level cash pressure and assumptions; it is not a forecast or guarantee.

### 4. Credit Passport — a traceable review snapshot

Packages synthetic-data disclosure, consent state, sources, evidence quality, financial indicators, rules-only risk notes, scenarios, illustrative EMI options, limitations, and a manual reviewer status. The assessment is snapshotted; new data requires a new assessment.

## What this is—and is not

- **Is:** a tested, deterministic prototype for organizing evidence and supporting human review.
- **Is not:** an approval/denial engine, validated default prediction, external verification service, live bank connection, or production lending system.
- **Data:** all showcase businesses and financial records are synthetic. Metrics in the demo describe these fixtures only.
- **Human control:** final review states are manual; the permitted statuses are pending, needs more information, and reviewed.

## Technical shape

React and TypeScript for the interface, FastAPI and SQLAlchemy for the backend, and pandas and NetworkX for the calculations. The single-server jury demo uses a temporary SQLite database. The development setup uses Supabase PostgreSQL.

## Judge walk-through

1. Open Business A and B; compare the same synthetic monthly revenue claim.
2. Show that evidence consistency differs while completeness and financial indicators remain their own dimensions.
3. Click a supplier in Trust Graph and inspect its linked records.
4. Apply sales-decline and combined-crisis assumptions; compare tenure EMIs.
5. Open the passport and finish at **Prepared for Human Lender Review**.

See [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for precise timings and fixture values, and [EVALUATION.md](EVALUATION.md) for test coverage and limitations. No real-world lending accuracy or fairness result is claimed.
