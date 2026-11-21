# Judge Q&A

## What is novel about CREDWEAVE AI?

The prototype brings fragmented business records into one traceable review flow: separate evidence completeness from reconciliation consistency, connect selected counterparties and records, show cash-flow scenarios, compare illustrative EMIs, and retain an immutable human-review snapshot. This is a product approach, not a claim of a novel or validated credit-scoring model.

## Is the data real? Are bank or UPI systems connected?

No. The two merchants, counterparties, invoices, transactions, and obligations are explicitly synthetic. Bank/UPI are simulated source labels; there is no live financial institution integration and no real repayment history. The seed can be reset deterministically.

## Does a match verify a transaction? Do unmatched records mean fraud?

No to both. A cross-source match only means available records align within documented amount/date tolerances; it does not establish that the transaction is genuine. An unmatched invoice, payment, or missing source is an evidence gap or unknown and needs human follow-up. Duplicate patterns are candidates for review, not accusations.

## Does the system predict defaults or decide eligibility?

No. The decision-support indicators are deterministic rules and descriptive financial metrics. There is no defensible labeled repayment-outcome dataset in this prototype, so the isolated synthetic ML method demo is not wired into the product. Loan affordability labels are scenario-dependent and never approve or deny credit.

## Has the system been proven fair?

No fairness outcome has been established. The prototype avoids using protected traits and discloses exclusion risks, but that is not a fairness certification. A production evaluation would need lawful, consented, representative outcome data, an approved feature policy, subgroup analysis, monitoring, and human governance.

## How is sensitive data protected?

The jury demo uses synthetic records in its own local database. The signed-in portal verifies accounts with Supabase and checks business ownership or a named lender consent grant on each request. Parsed records remain protected by the API. Production use with sensitive records still requires deployment and data-governance checks. [Security and deployment details](SECURITY_LIMITATIONS.md)

## Can it scale to production workloads?

That has not been measured. The graph uses in-process NetworkX, and this prototype has no throughput, load, or availability benchmark. It is designed to be runnable for a small demo, not to make a production scalability claim.

## What do the test results prove?

Tests establish expected behavior for code paths and planted synthetic cases, such as reconciliation, stress arithmetic, EMI calculations, consent gates, and passport snapshots. They do not measure real-world fraud detection, repayment performance, default prediction, lender outcomes, or business impact. The synthetic-only confusion matrix in `EVALUATION.md` must not be generalized.

## Why can both businesses have 100% completeness but different consistency?

Completeness asks whether expected source/period coverage is present. Consistency asks whether eligible invoice/payment records reconcile under explicit rules and includes duplicate-candidate effects. These dimensions intentionally remain separate; neither is a financial-risk score.

## Is the ₹2,00,000 request stored on each business?

No. It is the same hypothetical principal entered in the Loan Options comparison. The app does not persist a per-business funding-request field. Do not describe the demo input as an independently collected application request.
