# CREDWEAVE AI UI modernization

## Existing routes and access

| Audience | Routes | Access |
| --- | --- | --- |
| Public | `/`, `/login?role=owner\|lender\|admin`, `/register?role=owner\|lender`, `/forgot-password`, `/demo` | Public registration creates owner or pending lender accounts. The server checks the requested login role. |
| Owner | `/businesses`, `/account/recovery`, `/businesses/:id` | Own businesses only. The business route contains profile, upload consent, uploads, and source records. |
| Owner and authorized lender | `/businesses/:id/{verified-evidence,evidence-dna,trust-graph,financial-health,cashflow-twin,loan-options,credit-passport,review}` | Lenders require an individual grant and active passport-sharing consent. Lenders can record reviews. Only owners can reconcile evidence and run assessments. |
| Owner only | `/businesses/:id/assess` | Reads the current rules-based assessment and can generate a new one. |
| Pending lender | `/lender-setup`, `/account/recovery` | No business access. Admin approval is required. |
| Admin | `/admin` | Account list and role management. No financial workspace access. |
| Jury build | `/demo`, overview, stage choosers, and demo versions of workflows | Separate build and temporary SQLite database. Synthetic data and simulated verification stay labeled. |

## Components and contracts to preserve

- Vite, React, React Router and Tailwind. Retain `App.tsx`, `DashboardShell.tsx`, `lib/{api,portal,businessRoutes}.ts`, Cytoscape, Recharts, and the existing feature components. Keep the API client's cookie transport, single refresh, and expired-session handling.
- Supabase Auth behind `backend/app/auth.py`. Keep `GET /api/me`, `POST /api/auth/{login,register,refresh,logout}`, and `POST /api/auth/recovery/{setup,question,reset}`. Roles are server-resolved `owner`, `lender_pending`, `lender`, and `admin`. Recovery requires a generated recovery code and security answer. Admin is provisioned separately.
- `GET/POST /api/businesses` and `GET/PUT /api/businesses/{id}` support name, sector, city and operating months. Consent is `pending`, `granted`, or `withdrawn`. Records are paged with `kind` and `offset`. Uploads use multipart `file` under `/imports/{transactions,invoices,suppliers,obligations}`, limited to 2 MiB. Bank and UPI use the same transaction parser. Use `/sources` and `/records-summary` for import inventory and counts. Import statuses are `pending`, `imported`, and `failed`. Imports store normalized records with file hashes in PostgreSQL. No browser-facing Supabase Storage bucket or raw-file download exists.
- The business-scoped `/verified-evidence` endpoint returns current status counts, paginated provenance, and latest verification events. History is append-only at `/{provenance_id}/history`. `POST /reconcile` is owner-only. Status enum is `UNVERIFIED`, `PARTIALLY_SUPPORTED`, `SOURCE_VERIFIED`, `REQUIRES_REVIEW`, `SIMULATED_SOURCE_VERIFIED`. Evidence DNA and Credit Passport already read Gateway counts.
- `GET /evidence-dna`, `/evidence-findings`, `/trust-graph`, `/graph-findings`, and `/financial-summary` return calculated business-scoped snapshots. Graph nodes are Business, Counterparty, Invoice, and Transaction. Financial time-series values are observed inflows and outflows. Financial history and evidence are different concepts.
- `POST /assess` and `GET /assessments/latest` return versioned rules-based snapshots with `draft` or `ready` status. `GET /stress-tests/presets` and `POST /stress-tests` support revenue and expense changes, payment delay, duration, EMI, and seasonal weakness. `POST /loan-options` compares selected terms with observed data and supported scenario presets. Supplied scenario baselines are restricted to the jury demo.
- `GET /credit-passport` returns the latest assessment report, disclosures, consent and browser-print eligibility. The review workspace reads `GET /review-workspace` and writes `POST /reviews` with `pending`, `needs_more_information`, or `reviewed`. `GET /shares` and `PUT/DELETE /shares/{lender_id}` manage lender grants. `GET /api/admin/accounts` and `PUT /api/admin/accounts/{id}/role` implement the existing admin workflow.

## Gaps and implementation sequence

1. Shared navigation, fields, states, design tokens and public pages in `frontend/src/index.css`, `tailwind.config.js`, `components/ui.tsx`, `DashboardShell.tsx`, `PortalEntry.tsx` and `PasswordRecovery.tsx`. Preserve trusted roles, cookies, registration restrictions, and recovery behavior.
2. Owner workspace, registration, details, upload and lender queue in `BusinessPortal.tsx` and `OwnerProgress.tsx`. Split consent from registration, support file selection and validation, and derive progress from the selected authorized business. The repository has no account-wide activity feed, business delete API, or trusted bank/AA adapter.
3. Investigation tools in `VerifiedEvidencePage.tsx`, `EvidenceDnaPage.tsx`, `TrustGraphPage.tsx`, and `lib/api.ts`. Gateway's initial response lacks amount and record date. Add those using stored, business-scoped records and keep verification writes unchanged. Retain graph evidence and accessible tabular navigation without inventing relationships.
4. Analytics and export in `FinancialHealthPage.tsx`, `AssessmentPage.tsx`, `CashFlowTwinPage.tsx`, `LoanOptionsPage.tsx`, and `CreditPassportPage.tsx`. Use backend results, make limitations visible, and preserve print export. There is no trained production default model, forecast, or server PDF endpoint.
5. Human review and admin in `ReviewWorkspacePage.tsx`, `LenderSharing.tsx`, `AdminPortal.tsx`, and `OverviewPage.tsx`. Keep existing roles and revocation. The original app had no queue index. There is still no grant expiry, separate document request endpoint, or admin audit endpoint.
6. Regression checks with `npm --prefix frontend run lint`, `npm --prefix frontend exec -- tsc -b frontend/tsconfig.json`, `npm --prefix frontend test`, `npm --prefix frontend run build`, and `cd backend && .venv/bin/python -m pytest`. Use the temporary jury launcher for synthetic browser checks. Exercise the real portal flow with the existing authorized backend integration fixtures.

## Security boundaries

FastAPI owns business scoping. PostgreSQL enables row-level security and revokes direct client access to app tables. Scope every record lookup by business, clear page state when switching businesses, keep demo and live origins separate, and preserve the server-checked role on sign-in. No destructive migration is needed.


## Implemented API additions

| Contract | Result and authorization |
| --- | --- |
| `PATCH /api/businesses/{id}/upload-consent?granted=true\|false` | Owned business only. Returns the updated business without changing its profile or lender sharing grants. |
| `GET /api/businesses/{id}/verified-evidence` | Added record date, amount, display reference, source label, matching count, kind and search filters, and sorting. Authorization and audit history are unchanged. |
| `GET /api/lender/queue` | Approved lender only. Shows the lender’s consent-shared businesses and that lender’s latest status against each current assessment. |
| `GET /api/businesses/{id}/credit-passport` | Includes the latest allowed review status for the current assessment. Lenders see their own review entry only. |
| `POST /api/auth/register` | When the provider requires email confirmation, returns a confirmation state and issues no portal cookies. Recovery enrollment in that configuration is available after sign-in. |

## Manual verification

1. Use `./scripts/run-project.sh` for the signed-in portal. Register as an owner, save the recovery code when offered, sign out, and sign in again. If your provider requires email confirmation, open its confirmation link before signing in.
2. Register a business, save or edit its profile, and grant processing consent. In Data Sources, choose a CSV using the documented headers, check the staged filename, size, and detected columns, and submit. Confirm imported counts and recent source history.
3. Open the Gateway and try a status filter, source/reference search, and amount sort. Open a record and its history, then close the drawer with Escape. Check Evidence DNA and the graph against those records.
4. Compare a baseline and crisis CashFlow Twin scenario, select loan terms, and generate an assessment. Open the passport, grant access to an approved lender account, and use Print / Save PDF.
5. Sign in as that lender and record a human review. Revoke the grant as the owner, then verify the business leaves the lender’s queue and the original URL denies access.
6. Use `./scripts/run-jury-demo.sh` for the separate demo. Open the Twin Business Challenge and compare both synthetic businesses through Evidence DNA, Trust Graph, and Credit Passport.

## Product limits

- The deployment still controls Supabase email delivery. Health checks expose only API status. Recovery requires the saved code and security answer.
- No trusted bank or Account Aggregator adapter, raw document storage, or institutional verification workflow is configured. The upload screen accepts only documented transaction and evidence formats and reports server-confirmed imports. UPI entries can use the same bank statement. Potential overlapping imports are flagged for review, and there is no automatic cross-feed deduplication.
- No business deletion, lender grant expiry, separate document-request delivery, or admin audit feed exists. Review notes can record which information is needed, and grant revocation takes effect on subsequent requests.
- Credit Passport export uses the browser’s Print / Save PDF functionality behind the existing consent control. No server PDF-generation API exists.
- Risk analysis is rules-based. CashFlow Twin uses mathematical what-if inputs and no production predictive default model.

## Verification results

| Command or check | Result |
| --- | --- |
| `npm --prefix frontend run lint` | Passed |
| `npm --prefix frontend exec -- tsc -b frontend/tsconfig.json` | Passed |
| `npm --prefix frontend test` | 27 passed |
| `npm --prefix frontend run build` | Passed |
| `cd backend && .venv/bin/python -m pytest -q` | 86 passed |
| Isolated Chrome portal workflow | Registration, invalid and valid sign-in, recovery, profile edits, consent, CSV imports, Gateway history, Evidence DNA, graph, financial health, stress tests, loan options, assessment, browser PDF output, sharing, manual review, and revocation passed |
| Chrome responsive checks | Checked public, owner, lender, admin, and jury views at 375, 768, 1366, and 1680 px |
| Hosted services | Browser QA used a test auth provider and an isolated SQLite database. Live Supabase email delivery and deployment were outside the local test run. |
