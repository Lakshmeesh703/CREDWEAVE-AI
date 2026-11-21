# CREDWEAVE AI Evaluation

## Scope and honesty

This evaluation validates deterministic software behavior and synthetic demo fixtures. It does not validate real-world lending outcomes, fraud detection, repayment behavior, or probability-of-default accuracy. No real borrower or lender data is used.

## Ground-truth synthetic anomalies

The fixed fixture deliberately distinguishes two synthetic evidence profiles:

| Ground-truth planted condition | Business A — Sunrise Foods | Business B — Riverbend Repairs |
|---|---|---|
| Duplicate credit record candidate | Present | Absent |
| Unmatched receivable invoice | Absent | Present |
| Unmatched credit payment | Absent | Present |
| Stronger evidence consistency | Higher consistency profile | Gaps/conflicts profile |

These labels describe the fixture and derived findings, not accusations or fraud conclusions.

## Synthetic fixture assertions (not a detector benchmark)

The fixture tests assert that the planted duplicate-candidate category is present for Business A and that the planted unmatched-invoice category is present for Business B. A 2-by-2 table of those two category assertions would be correct by construction and is not a meaningful confusion matrix, precision/recall estimate, or anomaly-detection benchmark. No generalizable anomaly-detection performance metric is reported. The planted unmatched-payment condition is also asserted for Business B.

The tests confirm expected fixture behavior only; they do not establish detector performance on unseen or real records.

## Baseline comparison

The baseline is financial-only visibility: monthly cash flow, obligations, and trend alone.

The evidence-aware review adds:

- completeness and consistency as separate indicators;
- explicit uploaded-only, cross-source-consistent, externally-verified, disputed, and unavailable counts;
- source provenance and linked record IDs;
- planted duplicate/unmatched review findings;
- immutable passport traceability;
- human-review consent and audit controls.

In the seeded fixtures, Business A and Business B have the same synthetic ₹1,00,000 monthly sales claim and are compared using the same hypothetical ₹2,00,000 loan-options input. Both currently have 100 completeness; evidence-aware review exposes different consistency scores and reconciliation findings. The financial-only baseline has no evidence-quality visibility and therefore cannot distinguish those record-quality differences. The loan-options input is not a persisted funding request.

## Test coverage

### CSV and data intake

- Valid transaction import
- Duplicate file-hash rejection
- Invalid amount precision
- Missing required CSV columns
- Invalid ISO dates
- Transactional rejection on invalid data
- Cross-business 404 protection
- Source-upload consent block

### Evidence DNA

- Exact invoice/payment match
- Amount/date tolerance mismatch
- Duplicate candidate detection
- Missing periods/completeness
- Partial/unmatched records as unknown evidence
- Contrasting consistency profiles
- Provenance and externally-verified count remains zero

### Trust Graph

- Stable typed node and edge IDs
- `MATCHED_TO` relationship coverage
- Duplicate and unmatched findings
- Non-accusatory wording
- Supplier concentration arithmetic
- Synthetic provenance

### Financial health

- Refund/internal-transfer exclusion
- Hand-calculated net cash flow
- Sparse and negative months
- Zero inflow ratios without division-by-zero
- Obligations and supplier concentration

### CashFlow Twin

- Zero-shock identity behavior
- Negative result and cash gap
- Payment-delay cash conservation
- Combined 20% revenue decline, 15% expense increase, 45-day delay, and two weaker months

### Loan engine

- Standard independent EMI example
- 6/12/18/24-month tenures
- Zero interest
- Origination fee disclosure
- Rounding
- Negative post-EMI cash and DSCR review labels

### Passport, review, and consent

- 404 before assessment exists
- Immutable snapshot consistency
- Passport required disclosures and synthetic labels
- Latest snapshot traceability
- Separate upload/share consent
- Passport export gating
- Manual review statuses and checklist normalization
- Review timestamp/rule-version audit fields

### API integration

- Fixed seed loads two stable synthetic businesses
- Re-running the seed preserves a separate non-demo business while replacing only the fixed demo profiles
- Demo loading is blocked unless `DEMO_MODE=1` is explicit
- Business A and B proceed through identity, evidence, graph, financial summary, assessment, passport, and review APIs
- Synthetic contrast findings remain visible
- Demo-script claims, stress values, and EMI amounts match seeded API responses

### Frontend

- Health API unavailable friendly state
- Evidence cards keep completeness, consistency, and confidence separate
- Overview shortcuts resolve both synthetic profile names to their API-backed Evidence DNA routes
- Selecting a supplier shows its related synthetic payment record amounts, dates, and source IDs
- Dashboard navigation exposes all required menu labels
- Primary navigation and synthetic-demo banner use accessible roles/labels
- Responsive Vite build and TypeScript compilation
- Production dependencies and runtime routes

## Commands

Run from the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
python -m compileall -q app
python -m app.ml.synthetic_method_demo

cd ../frontend
npm ci
npm test -- --run
npm run lint
npm run build
npx tsc -b --pretty false
npm run dev
```

The standard development launcher reads `DATABASE_URL` from `.env`. Backend tests use in-memory SQLite, and jury mode creates an isolated temporary SQLite database.

## Pass/fail summary

Observed release-readiness revalidation:

- Backend: 44 tests passed, 0 failed.
- Python application bytecode compilation: passed.
- Isolated synthetic ML methodology demonstration: ran successfully; generated artificial labels only and is not connected to lending decisions.
- Frontend: 5 test files passed, 5 tests passed, 0 failed.
- Frontend lint: passed with no findings.
- Frontend TypeScript build/type check: passed.
- Frontend Vite production build: passed.
- Standalone runtime-validation plan: 4/4 assertions passed (production build, lint, home route HTTP 200, and Vitest 5/5).
- Seeded API journey and exact figures used by the demo script: covered by backend integration tests for both synthetic businesses.
- Scoped reset behavior, explicit demo-mode gate, and supplier-record details: covered by regression tests.
- Live Supabase reset and visual browser presentation: not run during this code-validation pass.

No accuracy or readiness percentage is inferred from test passes.

## Known false positives and limitations

- Duplicate candidates are record-pattern findings, not proof of duplicate activity or fraud.
- Cross-source matches indicate consistency only, not authenticity or external verification.
- Unmatched evidence is neutral unknown evidence and may reflect missing sources or record practices.
- Supplier concentration is a spend share, not a default-risk conclusion.
- Stress tests are deterministic scenario illustrations, not forecasts.
- EMI affordability labels require human review and are not eligibility or approval decisions.
- Synthetic labels and privacy controls do not replace real authentication, authorization, production audit logging, or data governance.
- The ML method demo uses artificial labels and has no real-world validity.
- Seasonal conclusions require caution with short histories.

## Remaining problems

Remaining observed issues:

- React Router 6.x reports two moderate production advisories under `npm audit --omit=dev`; the fix is a major React Router 7 migration and was not applied automatically to avoid an unsafe breaking upgrade.
- A full `npm audit` also reports additional development-tool advisories, including Vitest/Vite/tinypool; a forced audit fix would introduce breaking major upgrades on this Node 18 environment.
- The project currently runs Node 18.19.1. Clean install reports engine warnings for some transitive lint packages that require Node 20+; lint, tests, and build still pass.
- React Router future-flag warnings remain in Vitest output.
- FastAPI lifespan and SQLAlchemy UTC deprecation warnings remain.
- The frontend bundle is larger than Vite's 500 KB chunk advisory because of graph/chart dependencies.
- Browser Playwright recording is not a substitute for these HTTP/component tests; use a real browser in the final demo environment to verify visual layout and interactions.
- No real-world repayment dataset exists, so the synthetic ML demo remains excluded from lending decisions and is not an accuracy result.
