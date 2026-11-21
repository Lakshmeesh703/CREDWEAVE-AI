# Feature status

This inventory reports the current hackathon implementation, not a production-readiness certification.

| Module | Status | Implemented behavior | Boundary / remaining work |
|---|---|---|---|
| Business identity and onboarding | Implemented | Create/list/get business profiles; display consent state | Supabase account ownership; legal business identity requires independent verification |
| Evidence intake | Implemented | Transaction, invoice, and obligation CSV/JSON validation; bounded files; duplicate hashes; transactional imports; provenance | CSV imports; bank and UPI connectors are outside scope |
| Evidence DNA | Implemented | Separate completeness, consistency, categorical verification, confidence, claim trail, findings | Rule-based matching is not external verification; coverage rules are prototype-specific |
| Dynamic Trust Graph | Implemented | NetworkX typed nodes/edges, supplier concentration, candidate duplicates, unmatched items, source links | Findings are review prompts, not confirmed misconduct; graph scale not benchmarked |
| Financial Health | Implemented | Monthly transaction inflows/outflows/net cash flow, debt obligations, trend/volatility and coverage metadata | Cash flow is not accounting revenue/profit; classifications depend on available descriptions/markers |
| Explainable Risk Insights | Implemented, rules-only | Versioned indicators, evidence dimensions, confidence rationale, unknowns, lender follow-up questions | No probability of default and no outcome-validated predictive model |
| CashFlow Twin | Implemented | Deterministic revenue/expense shocks, delay timing approximation, monthly cash/EMI impacts | Not a forecast; delay uses a documented monthly approximation and observed-data limitations |
| Loan Options | Implemented, illustrative | Reducing-balance EMI, total repayment/costs, month-level affordability measures | No eligibility, approval, offered product, or recommendation guarantee |
| Credit Passport | Implemented | Latest immutable assessment, provenance, disclaimers, browser print-to-PDF | Requires an assessment snapshot; PDF is browser-generated, not server-rendered |
| Reviewer Desk | Implemented | Named, revocable lender grants and reviews tied to a verified reviewer and assessment | Review outcomes record human workflow progress |
| Synthetic demo lifecycle | Implemented for fixed fixtures | Explicit /demo route, stable Business A/B seed, prepared passports, overview shortcuts | Temporary local data resets on exit |
| Machine learning | Not part of lending flow | Isolated synthetic methodology demo exists | No defensible labeled repayment outcomes; no ML score is used by the app |
| Portal identity and roles | Implemented | Supabase Auth, server-side ownership and roles, account administration, PostgreSQL RLS | Verify the configured Supabase environment and review deployment operations before handling sensitive records |
| Real financial integrations and external verification | Planned | Not implemented | Requires authorized provider integrations, user consent, security review, data contracts, and validation |

## Cross-cutting product constraints

- Missing or unmatched evidence is unknown, not evidence of fraud or high default risk.
- A cross-source match is consistency only, not proof that the underlying transaction is genuine.
- Financial risk indicators, evidence completeness/consistency, verification status, and assessment confidence are distinct.
- Loan decisions remain with a human lender.
- All seeded demo data is synthetic, and outputs have no established real-world predictive validity.

For route inventory and data flow, see [ARCHITECTURE.md](ARCHITECTURE.md). For deployment requirements, see [SECURITY_LIMITATIONS.md](SECURITY_LIMITATIONS.md).
