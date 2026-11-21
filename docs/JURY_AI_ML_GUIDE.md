# CREDWEAVE AI — AI and ML concepts for the jury

## 30-second explanation

> Small businesses often have bank and UPI transactions, invoices, and supplier records spread across different sources. CREDWEAVE AI brings that evidence together. It shows which records agree, traces findings back to their sources, and lets a lender examine how changes in cash flow would affect repayment. The portal uses explainable rules, graph analytics, and financial simulations. We also built a separate logistic regression experiment on synthetic data. A human lender makes the credit decision.

## What we built into the product

| Feature | Concept used | What to show the jury |
| --- | --- | --- |
| **Verified Evidence Gateway** | Data validation, SHA-256 hashing, provenance and an append-only history | Open a record to show its source, verification reasons, limitations and history. Import checks look for issues such as repeated references, invalid values and running-balance discrepancies where balances are provided. A hash identifies file contents. Institutional verification requires an authenticated institutional source. The jury demo labels mock source verification as simulated. |
| **Evidence DNA** | Feature engineering and rule-based record linkage | Show **completeness**, **consistency**, and **verification status** separately. Completeness measures which expected months have transaction and invoice evidence. Consistency measures eligible invoice-to-payment matches and applies a deduction for duplicate-candidate groups. Verification status describes the support behind individual records. |
| **Dynamic Trust Graph** | A directed graph and relationship analytics | Show a supplier connected to the business and inspect source-linked invoice and payment records. NetworkX builds the graph; Cytoscape renders it. Duplicate candidates, unmatched records and supplier concentration help the lender decide what to review. |
| **Financial Health and Risk Insights** | Financial feature engineering and a transparent rules engine | Show operating inflows and outflows, debt burden, cash-flow volatility, and supplier concentration. The rules display each indicator’s value, thresholds and reason. Missing inputs can produce an **unknown** indicator. Evidence confidence describes the strength of available records. |
| **CashFlow Twin and Loan Options** | Deterministic scenario simulation and loan amortization | Change inflows, expenses or payment timing. Compare monthly cash before and after the installment. Loan Options calculates EMI, interest, repayment and a coverage ratio based on available cash and the proposed EMI. Every result depends on the inputs and assumptions. |
| **Credit Passport and Reviewer Desk** | Versioned snapshots, auditability and human review | Open the assessment date, sources, findings, scenario assumptions and limitations. Then show how a lender with an active grant records a review or requests more information in the review notes. |

## How the Verified Evidence Gateway evaluates a record

The Gateway applies rules to each record and shows the reason behind its status.

1. **Validate the upload.** The transaction CSV must have the required columns, valid dates and amounts, and unique references within the file. An invalid row or a repeated reference within the same file rejects the upload. The Gateway also rejects a byte-for-byte duplicate file for the same business using its SHA-256 hash.
2. **Flag issues in accepted records.** A missing description, a similar entry in an earlier upload, or a running balance that disagrees with the transaction can trigger **Requires review**. When balances are supplied and usable, the check adds a credit to the previous balance or subtracts a debit and compares the result with the next reported balance. Accepted uploads without findings start as **Unverified**.
3. **Compare supporting records.** When the owner selects **Compare supporting records**, the Gateway uses Evidence DNA matching to compare a receivable invoice with an incoming payment. A match from different uploaded sources can give both records **Partially supported** status. A duplicate-candidate finding takes priority, and an existing **Requires review** flag remains visible after matching.
4. **Record what changed.** Each change adds a history entry with the method, timestamp, reasons, supporting record references and limitations. The original source metadata and file hash stay linked to the record.

In the Gateway integration test, a ₹1,000 incoming payment and a ₹1,000 invoice from separate uploads both started as **Unverified** and became **Partially supported** after comparison. A separate ₹25 debit remained **Requires review**. It had no description, and the reported balance was ₹500 when the rule expected ₹975 after the debit.

Matching shows that uploaded records agree. The SHA-256 hash identifies the uploaded file for comparison. The portal has no live institutional verification connection, and the demo labels its mock-source records **Simulated source verification**. [Gateway implementation](../backend/app/services/gateway.py) · [Gateway integration test](../backend/tests/test_portal.py)

### How Evidence DNA matches invoices and receipts

Evidence DNA compares each eligible receivable invoice with candidate credit transactions. It looks for an amount difference within the greater of **₹100 or 1% of the invoice amount**, dates within **14 days**, and the same counterparty when both records identify one. Each credit transaction can be used once. When multiple transactions qualify, the rule prefers the closest date.

A matched invoice and payment provide corroboration. A repeated pattern or an unmatched invoice gives the reviewer a specific follow-up. The rules alone cannot establish authenticity or fraud. See the [matching implementation](../backend/app/services/evidence_dna.py) and [Gateway status definitions](VERIFIED_EVIDENCE_GATEWAY.md).

## Where we actually used machine learning

We built an isolated **supervised binary classification** experiment with scikit-learn. It demonstrates how a model can be trained, evaluated and interpreted when labeled examples are available.

1. **Features.** Six engineered inputs represent expense-to-inflow ratio, debt burden, negative cash-flow months, cash-flow volatility, supplier concentration, and average monthly net cash.
2. **Training labels.** A seeded generator creates four synthetic entities with 100 rows each. It assigns artificial labels from a known formula and random sampling. These labels describe the simulation.
3. **Evaluation split.** We train on three entities and hold out the fourth, giving **300 training rows and 100 test rows**. Holding out a whole entity prevents rows from the same entity appearing in both sets.
4. **Model.** `StandardScaler` puts features on comparable scales. **Logistic regression** combines those scaled features and passes the result through a sigmoid to estimate the probability of the synthetic positive class.
5. **Interpretation.** Standardized coefficients show how each feature contributes to the model’s prediction with the other inputs held fixed. The coefficients describe the fitted synthetic model.

**Synthetic experiment results from the fixed seed.** ROC-AUC was **0.750**, average precision was **0.868**, and Brier score was **0.186**. ROC-AUC measures ranking across the two artificial classes, average precision summarizes precision and recall for the artificial positive class, and Brier score measures squared probability error. These results apply to one held-out synthetic entity and provide no estimate of real borrower repayment performance. The experiment runs separately from the portal and lender workflow. See the [evaluation notes](ML_EVALUATION.md) and [experiment code](../backend/app/ml/synthetic_method_demo.py).

Run from the repository root after installing dependencies.

```bash
(cd backend && .venv/bin/python -m app.ml.synthetic_method_demo)
```

## What to demonstrate

1. Open the **Twin Business Challenge**. Both fictional businesses report the same **₹1,00,000 monthly sales claim**. Both score **100/100 for completeness**, while Sunrise Foods scores **90/100 for consistency** and Riverbend Repairs scores **43/100**.
2. Explain the difference. Sunrise matches **6 of 6** eligible invoices and loses 10 points for a planted duplicate-candidate group. Riverbend matches **3 of 7** eligible invoices. Show the source trail for one finding.
3. Open **CashFlow Twin** and apply **Combined crisis**. Explain how lower inflows, higher expenses, delayed receipts and weaker months change the cash available for repayment. Compare two loan terms to show the monthly installment and total interest trade-off.
4. Open the **Credit Passport** and end with **Prepared for Human Lender Review**. Show how the lender can inspect evidence and record a decision about review progress. Use the [four-minute demo script](DEMO_SCRIPT.md) for click-by-click steps.

## Questions the jury may ask

**Does the portal use a trained model or an LLM to make decisions?** The portal uses deterministic rules and financial calculations. The logistic regression experiment runs offline on artificial labels. The lender records the human review.

**Can the product predict defaults or find fraud?** It surfaces traceable evidence gaps and cash-flow pressures for investigation. A valid prediction claim would require consented and documented repayment outcomes, checks for data leakage, validation on new businesses and later periods, and a fairness evaluation.

**Why use rules in the product today?** Every finding can be traced to a specific record, formula or threshold. That allows a lender to check the reason and ask for more evidence when the available data is incomplete.
