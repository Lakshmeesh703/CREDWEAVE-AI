# CREDWEAVE AI — Step-by-Step GitHub Copilot Build Prompts

> **Project name:** CREDWEAVE AI (not CREDWEAVE AI 2.0)  
> **Hackathon track:** Finance — F2: Credit for the Credit-Invisible  
> **Goal:** Build a working, explainable, evidence-aware lending decision-support prototype using VS Code + GitHub Copilot.  
> **Audience:** Small-business applicants and human lending reviewers.  
> **Prototype data:** Fully synthetic; any bank/UPI connector is simulated. **Never claim that synthetic-data outcomes validate real-world credit risk.**

## How to use this guide

1. Open **VS Code** with **GitHub Copilot Chat** enabled. Create an empty folder named `credweave-ai` and open it in VS Code.
2. Set Copilot Chat to **Agent mode** (or the available edit-capable mode) so it can create and change workspace files.
3. Paste **Prompt 00** first, then run **one prompt at a time in order**. Inspect changes, run the specified tests, fix errors, and commit before moving on.
4. If Copilot tries to implement everything in one go, tell it: **“Only implement the current prompt. Do not begin the next phase.”**
5. At the end of each stage, ask Copilot for **files changed, commands run, test results, assumptions, and remaining limitations**. Do not accept claims without running the app or tests yourself.
6. **Suggested priority:** Get through **Prompts 00–09**, plus 12 and 14, before polishing extras. Prompts 10–11 extend the core prototype; Prompt 13 adds optional ML.

### Recommended architecture

```text
credweave-ai/
├── frontend/                  # React + Vite + TypeScript + Tailwind
│   ├── src/
│   └── ...
├── backend/                   # Python + FastAPI + SQLAlchemy + SQLite
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/
│   └── ...
├── data/                      # synthetic fixtures; never real user records
├── docs/                      # architecture, evaluation, demo and decisions
├── scripts/
├── .github/workflows/
├── .env.example
├── .gitignore
└── README.md
```

**Suggested technologies:** React, Vite, TypeScript, Tailwind CSS, Recharts, Cytoscape.js; Python 3.11+, FastAPI, Pydantic, SQLAlchemy, pandas, NetworkX, pytest; SQLite for the hackathon. Use simple deterministic rules before adding a credit-risk model. Avoid extra infrastructure (Redis, Kafka, Docker, cloud services) until the local demo works.

---

## Prompt 00 — Establish project rules and implementation plan

**Paste into Copilot Agent:**

```text
You are my senior full-stack engineer, ML engineer, and product architect. We are building CREDWEAVE AI, a hackathon prototype for Finance F2: Credit for the Credit-Invisible.

MISSION: Help lenders examine credit-invisible small businesses using fragmented financial records, evidence reconciliation, a business trust graph, financial health metrics, stress testing, and transparent loan options. The system supports, but NEVER replaces, the human lender's decision.

NON-NEGOTIABLE PRODUCT PRINCIPLES:
1. Keep financial risk, evidence completeness, evidence consistency, verification status, and assessment confidence separate. Do not merge them into one unexplained score.
2. Missing records are unknown evidence, not automatically fraud or high default risk.
3. A matching invoice/payment proves consistency, NOT that the underlying transaction is genuine.
4. All demo data is clearly marked SYNTHETIC. Simulated bank/UPI data is not represented as a real integration.
5. No automatic loan approval/denial. All recommendations are illustrative and require a human reviewer.
6. Use INR, Indian-style business scenarios, and correct EMI calculations.
7. Privacy by design: minimum necessary data, explicit consent status, masked account identifiers, no hardcoded secrets, no real PII in the repository.
8. Explain assumptions, uncertainty, limitations, and rule/model versions in every assessment.
9. Keep the implementation modular, runnable on a developer laptop, tested, and demo-ready.

DESIRED NINE-STAGE FLOW:
1 Smart Business Identity
2 Multi-Source Data Intelligence
3 Evidence DNA Engine
4 Dynamic Trust Graph
5 Financial Health Intelligence
6 Explainable Risk Intelligence
7 CashFlow Twin 2.0
8 Adaptive Loan Structuring
9 Explainable Credit Passport
=> Human Lender Review

STACK: frontend React/Vite/TypeScript/Tailwind, backend FastAPI/Pydantic/SQLAlchemy/SQLite, pandas, NetworkX, Recharts and Cytoscape.js. Use pytest for backend and Vitest/React Testing Library for frontend. Prefer deterministic, auditable calculations over unverified ML claims.

TASK FOR THIS PROMPT ONLY:
- Inspect the current workspace.
- Create docs/IMPLEMENTATION_PLAN.md with architecture, module boundaries, data flows, prioritized milestones, user journeys, acceptance criteria, and risks.
- Create docs/DECISIONS.md recording design assumptions and key tradeoffs.
- Propose a canonical backend API contract, but do not implement it yet.
- Create a concise root README.md explaining the prototype and synthetic-data limitations.
- At the end, tell me the exact next action and stop. Do not scaffold code yet.
```

**Done when:** Plan and decisions exist; scope is realistic; no implementation is started prematurely.

---

## Prompt 01 — Scaffold the monorepo and developer environment

```text
Implement only the scaffold for CREDWEAVE AI in the existing workspace, following docs/IMPLEMENTATION_PLAN.md.

1. Create frontend/ using Vite + React + TypeScript and install/configure Tailwind. Add React Router, Axios (or fetch abstraction), Recharts, Cytoscape.js, and a tidy component directory.
2. Create backend/ using FastAPI, Pydantic v2, SQLAlchemy 2, SQLite, pandas, NetworkX and pytest. Use Python virtual environment .venv under backend/ (not committed).
3. Add backend/app/main.py with GET /api/health returning service status and version. Configure CORS for local development only, via environment variable.
4. Add .env.example containing non-secret variables: API_BASE_URL, CORS_ORIGINS, DATABASE_URL, APP_ENV, DEMO_MODE.
5. Create strong .gitignore covering .venv, node_modules, .env, *.db, __pycache__, build artifacts, and generated exports. Do NOT commit virtual environments or personal data.
6. Add scripts for starting frontend and backend and provide exact Linux/Ubuntu terminal commands in README.md.
7. Make frontend show a simple CREDWEAVE AI landing screen and backend health status; show a friendly error if API is unavailable.
8. Add initial smoke tests and run the commands that are available. Fix issues before stopping.

Return: files created, commands to install/start, localhost URLs, and test results. Do not implement product modules yet.
```

**Run (adapt if scaffold differs):**

```bash
# Terminal 1
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Terminal 2 (from repository root)
cd frontend
npm install
npm run dev
```

**Done when:** frontend loads, API health endpoint works, and `.venv/`, `node_modules/`, `.env`, and databases are ignored by Git.

---

## Prompt 02 — Define the database, contract, and synthetic seed data

```text
Implement the CREDWEAVE AI data model and synthetic dataset. Do not implement business analytics yet.

Create SQLAlchemy tables and Pydantic request/response models for:
- Business(id, name, sector, operating_months, city, consent_status, created_at)
- DataSource(id, business_id, kind, synthetic, source_label, imported_at, file_hash, parsing_status)
- Transaction(id, business_id, source_id, external_ref, transaction_date, amount_inr, direction, counterparty_id, payment_channel, description, currency)
- Invoice(id, business_id, source_id, invoice_no, issued_at, due_at, total_inr, counterparty_id, direction, status)
- PaymentLink(id, business_id, invoice_id, transaction_id, linked_amount_inr, match_method, match_status)
- Counterparty(id, business_id, name, type, identifier_masked)
- Obligation(id, business_id, monthly_payment_inr, description)
- Assessment(id, business_id, created_at, rule_version, status, snapshot_json, limitations_json)
- Review(id, assessment_id, reviewer_name_or_alias, status, reason, updated_at)

Use DECIMAL/NUMERIC for monetary data, ISO dates, IDs, validated enums, and appropriate uniqueness constraints. Use consistent Indian rupee units and document the schema.

Generate a fixed-seed, fully synthetic dataset: two demonstration merchants (Business A and Business B), each claiming ~₹1,00,000/month sales and seeking ₹2,00,000 funding, but with contrasting evidence quality. Include at least 6 months of transactions, invoices, counterparties, obligations, duplicates, unmatched invoices/payments, and supplier concentration examples. Do not encode conclusions as database facts; let later engines derive them.

Create repeatable seed command, database init/migration strategy, fixtures, schema tests, and docs/DATA_DICTIONARY.md. Ensure seeds can be rerun safely and explicitly label all rows SYNTHETIC. Keep example files in data/synthetic/.

Stop after schema, synthetic fixtures, and tests. Return exact seed/test commands.
```

**Done when:** One command creates consistent sample businesses, without duplicate rows on rerun.

---

## Prompt 03 — Business onboarding and evidence upload APIs

```text
Implement CREDWEAVE AI Stages 1–2: business onboarding and multi-source intake, following our data dictionary.

Backend APIs under /api:
- POST /businesses (new business, consent status)
- GET /businesses
- GET /businesses/{id}
- POST /businesses/{id}/imports/transactions (CSV file)
- POST /businesses/{id}/imports/invoices (CSV file)
- POST /businesses/{id}/imports/obligations (CSV or JSON)
- GET /businesses/{id}/sources
- GET /businesses/{id}/records-summary

Build strict CSV column validation, human-readable parse errors, row-level rejection reports, file-size limits, currency/date normalization, duplicate-import prevention using file hashing, and transactional ingestion (no partially applied invalid imports). Prevent IDOR-style cross-business record access in the prototype service design; clearly document that production requires proper authentication and authorization.

Frontend: business list, new-business form, consent indication, profile page, and a clear import interface with preview/validation results. Offer a button to load synthetic demo data. Visibly mark all synthetic datasets and simulated integrations.

Add backend API tests, CSV edge-case tests, and basic frontend component tests. Run and fix tests. Do not implement the Evidence DNA engine yet.
```

**Done when:** a user can select either business and upload validated CSV evidence.

---

## Prompt 04 — Build Evidence DNA (the signature feature)

```text
Implement Stage 3: the CREDWEAVE AI Evidence DNA Engine. This is the signature feature and must be explainable and reproducible.

Create backend/app/services/evidence_dna.py with deterministic, unit-tested logic. For each business compute and return SEPARATE indicators:
A. Evidence completeness (0–100) based on explicitly documented expected fields/periods, with 'not applicable' excluded from denominators.
B. Evidence consistency (0–100) based on reconciliation rules and documented denominator. Include invoice/payment amount and date tolerances, duplicate record checks, and unexplained discrepancies.
C. Verification status as categorical counts: uploaded-only, cross-source-consistent, externally-verified (typically zero in this synthetic prototype), disputed, unavailable.
D. Assessment confidence label derived from coverage and reconciliation quality, with clear rule-based rationale. It is NOT a statistical confidence interval.

CRITICAL: an unmatched record is not necessarily suspicious; different source availability affects possible comparisons. Never describe cross-source matches as independent authentication. Never automatically infer fraud or poor creditworthiness from missing records.

For every finding return: code, severity, human-readable explanation, linked source IDs, record IDs, amounts involved, check performed, and recommended follow-up. Include source provenance and rule_version. Implement a clear 'claim-to-evidence' trail for the reported monthly revenue claim.

Endpoints:
GET /api/businesses/{id}/evidence-dna
GET /api/businesses/{id}/evidence-findings

Frontend: Evidence DNA page with three distinct metric cards, breakdown tables, status chips, and clickable findings that reveal supporting records. Keep explanation text readable and accessible. Provide unit tests for exact matching, partial matching, duplicated invoices, missing periods, and intentionally inconsistent records. Do not create false 'verified' labels.

STOP once backend + UI + tests work. Show example JSON and tests run.
```

**Done when:** Business A and B show different evidence **quality**, with transparent reasons and linked records.

---

## Prompt 05 — Build the interactive Dynamic Trust Graph

```text
Implement Stage 4: Dynamic Trust Graph for CREDWEAVE AI.

Backend: use NetworkX (not a graph database for MVP) to assemble a graph with typed nodes: Business, Counterparty, Invoice, Transaction; and typed edges: SOLD_TO, PURCHASED_FROM, INVOICED, PAID, MATCHED_TO. Every graph element must link back to a source record; avoid inventing business relationships.

Implement auditable analytics:
1. Duplicate invoice identifiers or suspected duplicates (explain the matching rule).
2. Unmatched invoices and unmatched payments.
3. Counterparty/supplier concentration (% of total spend by top supplier).
4. Unusual repeated patterns flagged for review, never labeled as proven fraud.

Endpoint GET /api/businesses/{id}/trust-graph returns nodes, edges, anomalies, metrics and provenance; optionally GET /api/businesses/{id}/graph-findings.

Frontend: implement responsive interactive graph using Cytoscape.js. Different colors/shapes for node types, pan/zoom, filters by entity and finding type, a legend, graph summary KPIs, and a side panel that opens when a node/edge is clicked: amount, date, linked invoice/payment, verification status, and source. Avoid displaying personal financial account numbers.

Test graph construction, stable IDs, concentration calculations, and false-positive wording. Keep graph usable with 100+ records and allow limiting display to relevant subgraphs. Stop when demo data renders and click-through evidence works.
```

**Done when:** judges can click a supplier and inspect its invoices and payments.

---

## Prompt 06 — Financial Health Intelligence

```text
Implement Stage 5: financial health intelligence without using an ML default-risk score.

Build audited calculations from normalized transactions and obligations:
- Monthly inflows and outflows (distinct from invoice totals; avoid double counting)
- Net operating cash flow by month
- Revenue trend and growth, only when the source definition supports it
- Expense-to-inflow ratio
- Cash-flow volatility and positive/negative months
- Supplier concentration from graph data
- Existing monthly debt obligations
- Seasonality observations with an explicit warning when history is insufficient

Each metric must include units, date window, exact formula or method, data coverage, and caveats. If profit is not supportable from available data, do NOT present cash flow as accounting profit; label it 'net cash flow' instead. Handle refunds and internal transfers correctly and avoid treating every incoming transaction as revenue.

Endpoint GET /api/businesses/{id}/financial-summary.
Frontend: financial overview with monthly charts in Recharts, period filters, source coverage notice, missing-data warning, and key metrics. Unit-test the calculations against small hand-worked fixtures and synthetic seeds.

Stop after this stage; provide a correctness checklist.
```

**Done when:** charts agree with database totals and have understandable definitions.

---

## Prompt 07 — Explainable Risk Intelligence (rules-first)

```text
Implement Stage 6: transparent credit decision-support indicators. DO NOT train or claim a predictive default model without legitimate, labeled repayment outcome data.

Create a RULES-ONLY prototype that evaluates factors such as cash-flow variability, debt burden, negative cash-flow months, and supplier concentration. It should output:
- Financial risk indicators and why they were flagged (not a validated probability of default)
- Evidence completeness/consistency independently from the Evidence DNA service
- Assessment confidence independently from risk, with its derivation documented
- Key risk factors, mitigating factors, unknowns, recommended questions for lender review
- Versioned thresholds in a config file with tests and documentation

Avoid protected traits and obvious proxies; document fairness and potential exclusion concerns. No automatic accept/reject or creditworthiness claims based on missing documents alone. Write /docs/RISK_MODEL_LIMITATIONS.md explaining rule-based heuristics vs real supervised credit risk prediction.

Endpoint POST /api/businesses/{id}/assess to create an immutable snapshot; GET /api/businesses/{id}/assessments/latest.
Frontend: separate Financial Indicators, Evidence Quality, and Assessment Confidence panels; explainability drawer for each factor. Add tests where businesses with identical finances but different evidence coverage do not automatically receive different default-risk probabilities.

Do not implement optional ML in this prompt.
```

**Done when:** two different evidence profiles are transparent without an unsupported repayment prediction.

---

## Prompt 08 — CashFlow Twin 2.0 stress testing

```text
Implement Stage 7: CashFlow Twin 2.0. This is a deterministic scenario calculator, NOT a validated forward-looking forecast.

Create scenario API POST /api/businesses/{id}/stress-tests. Inputs: base monthly inflow/outflow model, revenue_shock_pct, expense_shock_pct, payment_delay_days or a documented monthly timing approximation, duration_months, and selected loan EMI. Return monthly projected inflows, outflows, net cash, EMI coverage, minimum liquidity or cash gap, warnings, and a before/after comparison.

Provide presets:
A Normal operations
B Sales decline: -20% revenue
C Supplier cost increase: +15% expense
D Seasonal disruption: two consecutive weaker months
E Combined crisis: -20% revenue, +15% expense, delayed payments

Model delayed customer payments as cash-timing shifts without accidentally deleting money; clearly document simplifying assumptions. Use base months with observed data coverage and show warnings when data are incomplete. Avoid presenting scenarios as guaranteed outcomes.

Frontend: five preset cards, editable sliders, comparison chart, month-by-month table, and side-by-side metrics. Make changes recalculate through one canonical backend algorithm. Add tests for zero shocks, negative results, delay cash conservation, and combined crisis.

Stop after stress-testing is functional.
```

**Done when:** a judge changes the revenue shock and the cash/repayment chart updates correctly.

---

## Prompt 09 — Adaptive Loan Structuring

```text
Implement Stage 8: illustrative loan structuring and affordability analysis.

Create POST /api/businesses/{id}/loan-options. Inputs: requested principal_inr (e.g., ₹2,00,000), annual_interest_rate_pct, tenure_months list [6,12,18,24], optional origination fee, and a selected CashFlow Twin scenario.

Calculate with Decimal or clearly controlled rounding:
monthly_rate = annual_interest_rate_pct / (12 * 100)
EMI = P*r*(1+r)^n / ((1+r)^n - 1)
For zero-interest loans, EMI = P/n.
Also return total repayment, interest cost, optional disclosed fees, monthly net cash after obligations and proposed EMI, and month-level debt-service coverage as a transparent measure (define the numerator and handling of zero/negative denominators).

Mark options 'may be affordable under the specified scenario' or 'requires review'; avoid claiming eligibility, recommending an amount as guaranteed, or making approval decisions. Make thresholds configurable and explain assumptions. Do not use a single average monthly inflow where seasonal shortfalls matter.

Frontend: compare tenures in a table and chart; adjustable principal and interest; link to stress-test selection; show 'why' and tradeoffs for each option. Include tests against independently calculated EMI examples, zero-interest rates, rounding, and negative cash months.

Stop when a judge can compare four options and see stressed affordability.
```

**Done when:** 6/12/18/24-month options display correctly, with auditable calculations.

---

## Prompt 10 — Explainable Credit Passport + export

```text
Implement Stage 9: Explainable Business Credit Passport as the final review artifact.

Create a lender-readable assessment view containing:
- business details and assessment ID/date
- synthetic-data disclosure and consent state
- source inventory and provenance
- Evidence DNA: completeness, consistency, verification counts, missing evidence
- Trust Graph: concentration/anomaly findings with links to records
- financial health metrics with coverage windows
- rule-based risk indicators (or properly labeled validated model, if available)
- CashFlow Twin scenario outcomes and assumptions
- illustrative EMI/loan option comparisons
- top strengths, unanswered questions, limitations, rule version
- status: 'Prepared for Human Lender Review' (NEVER 'Loan Approved')

Use a reproducible assessment snapshot; if underlying business data change, a new assessment must be created instead of silently modifying historical reports.

Backend GET /api/businesses/{id}/credit-passport, with a PDF export endpoint if practical; secure report filename, no embedded secrets or sensitive unmasked identifiers. Frontend: attractive print-friendly passport, source links, print/download action. If PDF export is fragile, ship browser print-to-PDF first, then add server export.

Write snapshot tests confirming all values match the current assessment and disclaimers appear. Stop after end-to-end passport works.
```

**Done when:** every displayed result can be traced to a record, calculation, or disclosed rule.

---

## Prompt 11 — Human lender review and consent controls

```text
Implement the human review layer without building a full bank-grade identity system.

Add a lender reviewer demo page showing the latest passport, evidence findings, scenario comparisons, and an explicit human-review checklist. Allow a reviewer to record a comment and set REVIEW_STATUS: pending, needs_more_information, reviewed (not automated approval). Record timestamp and rule/version reference.

Include applicant consent flags for source upload and passport sharing; if consent is absent, block share/export actions and explain why. Implement demo-only role separation in UI and service layers; clearly disclose that proper authentication/authorization is required before production use.

Add privacy safeguards: masked identifiers, file size checks, logs free of raw financial CSV rows, data deletion/reset for synthetic demo. Test consent checks and review audit logging. Keep all review actions manual.
```

**Done when:** the workflow ends with a documented, human-controlled review status.

---

## Prompt 12 — Make the whole UI polished and connected

```text
Perform an integration and UI/UX pass across the complete CREDWEAVE AI application; do not rewrite working logic.

Create an attractive, professional fintech dashboard theme (dark navy + emerald accent), responsive for desktop and mobile, accessible labels and keyboard interactions, consistent typography and color contrast. Navigation:
Overview | Businesses | Data Sources | Evidence DNA | Trust Graph | Financial Health | Risk Insights | CashFlow Twin | Loan Options | Credit Passport | Reviewer Desk

Add clean loading/empty/error states, demo mode banner, contextual explanations, breadcrumbs, tooltips for formulas, and one-click access to the two synthetic businesses. Ensure frontend calls actual backend APIs; remove hardcoded dashboard values except explicitly labeled demo placeholders. Protect against empty datasets, API errors, and inconsistent schema.

Build a clear step-by-step user journey on the Overview page and ensure no screen claims 'AI predicted default' if only rule-based analysis exists. Run frontend lint/type checks and backend tests. Stop and report any unresolved integration issues.
```

**Done when:** every menu item leads to a working screen with real API data.

---

## Prompt 13 — OPTIONAL: Machine learning only if defensible

> **Skip this stage** if you do not have appropriately labeled repayment outcomes. A working, transparent rules-based prototype is better than an unsupported “95% accuracy” claim.

```text
OPTIONAL EXTENSION ONLY. Before implementing any supervised credit-risk ML, check whether the workspace contains ethically usable, sufficiently documented, labeled repayment outcome data with consent/license and known provenance. If not, STOP and report 'No defensible repayment prediction training data available'; suggest an optional synthetic-only method demonstration with no real-world accuracy claims.

If suitable data exist, create a reproducible ML experiment in a separate module: train/test split by time/entity as appropriate, leakage audit, baseline Logistic Regression, Random Forest challenger, feature documentation, ROC-AUC/PR-AUC/calibration/confusion matrix as appropriate, uncertainty reporting, subgroup fairness checks where legally/ethically supported, and explainability (coefficients or SHAP if compatible). Clearly label the dataset and limitations in docs/ML_EVALUATION.md.

Never feed evidence verification status into default-risk probability without demonstrating validity and fairness. Keep rules-based pipeline as fallback. Do not show production-ready probability of default based solely on toy synthetic labels.
```

---

## Prompt 14 — Evaluation, integration tests, and honesty checks

```text
Act as QA lead for CREDWEAVE AI. Audit the entire repository. Fix defects without hiding failed tests or inventing performance metrics.

REQUIRED AUTOMATED TESTS:
1. CSV parser: good, bad, missing column, duplicate import, invalid dates.
2. Evidence DNA: exact match, partial mismatch, duplicates, missing data, source status and provenance.
3. Graph: stable node/edge IDs, unmatched records, concentration arithmetic.
4. Finance: refunds, internal transfers, sparse months, negative cash flow, zero values.
5. Scenarios: no-shock identity, 20% revenue drop, 15% cost increase, two-month seasonal downturn, delayed payment timing.
6. Loan engine: zero and nonzero interest, 6/12/18/24 month EMI, rounding and debt-service coverage.
7. Passport: reproducible snapshots, traceability, missing-data limitations, synthetic labels.
8. Review: explicit consent and human-only status changes.
9. API integration: seeded Business A and B from onboarding through passport.
10. UI: frontend build, TypeScript check, accessibility smoke check, no dead navigation.

Create docs/EVALUATION.md with exactly what was tested, ground-truth labels for deliberately planted synthetic anomalies, confusion matrix/precision/recall for anomaly detection where meaningful, a baseline comparison (e.g., financial-only vs evidence-aware review visibility), known false positives, and serious limitations. Clearly distinguish technical test accuracy from real-world lending outcomes.

Run all tests, frontend build, lint, and type checks. Give me the exact commands and truthful pass/fail summary. Fix failures that can be fixed safely and explicitly list any remaining problems.
```

**Done when:** the end-to-end demo works from a clean install and metrics are backed by tests.

---

## Prompt 15 — Script the winning live demo

```text
Prepare a reliable 3–4 minute live demonstration for CREDWEAVE AI using the two synthetic merchants.

Create scripts/reset_demo.py or an equivalent deterministic reset command. Add DEMO_MODE=1 and simple UI entry buttons for 'Business A — stronger evidence' and 'Business B — evidence gaps'.

Demo sequence:
0:00 Introduce the credit-invisible problem.
0:25 Open two merchants: same reported ₹1,00,000 monthly revenue; both request ₹2,00,000.
0:50 Compare Evidence DNA — follow a specific revenue claim into invoices and payments.
1:25 Open Trust Graph — click one supplier and reveal records; show duplicate/unmatched finding.
2:00 Compare financial health while emphasizing evidence reliability ≠ default risk.
2:25 Run a -20% sales shock and combined crisis in CashFlow Twin.
3:00 Compare 6/12/18/24-month illustrative EMI options.
3:25 Show Credit Passport, source trail, uncertainty and human review.

Create docs/DEMO_SCRIPT.md, docs/JUDGE_QA.md (answers to likely challenges about novelty, synthetic data, false positives, fairness, data security, scalability, and results), and docs/DEMO_RECOVERY.md for offline/no-network failures.

Check every click and number against actual backend output. Never describe unimplemented features as working. Provide a concise list of final demo steps.
```

---

## Prompt 16 — Final repository, README, and presentation checklist

```text
Do a release-readiness pass for the CREDWEAVE AI hackathon submission.

1. Rewrite README.md with problem statement (Finance F2), project pitch, architecture diagram (Mermaid text), prerequisites, Linux/Ubuntu install commands, .env setup, seed command, how to run both apps, tests, feature matrix, known limitations, synthetic-data notice, privacy/security notes, and screenshots placeholders.
2. Add docs/ARCHITECTURE.md with data flow and API endpoints, docs/FEATURE_STATUS.md identifying implemented / partial / planned modules, and docs/SECURITY_LIMITATIONS.md with no-production-use warning.
3. Make sure git status has no .venv, node_modules, .env, secrets, raw personal records, or unintended large binaries. Never delete user data without permission.
4. Run all checks from Prompt 14. If scripts fail, report that explicitly.
5. Create a compact judge-facing one-page summary of Evidence DNA, Trust Graph, CashFlow Twin and Credit Passport.
6. Give me an exact clean-install and demo checklist to follow at the event.

Do NOT add speculative claims about credit approval, fairness achieved, or predictive model accuracy.
```

---

## Quick checkpoint prompts (use after *every* stage)

### Checkpoint A — Review and test

```text
Review only the code added in the current phase. Run relevant tests and type checks; identify bugs, security concerns, missing data provenance, misleading financial claims, and inconsistent API shapes. Fix the issues you can verify, then summarize PASS/FAIL honestly. Do not move to the next phase.
```

### Checkpoint B — Explain the code to me

```text
Explain the current phase like I'm presenting it to hackathon judges: what it does, which files implement it, what algorithm/formula it uses, its limitations, and one live demo example. Then show how to run and test it locally.
```

### Checkpoint C — Fix a specific error

```text
I encountered this error while executing the current CREDWEAVE AI phase:
[PASTE FULL TERMINAL ERROR]

Diagnose the root cause using repository context, propose the smallest safe fix, apply it, rerun the failing command, and show exactly what changed. Do not replace working architecture or skip the failing test.
```

### Checkpoint D — Commit safely

```text
Inspect git status and .gitignore. Confirm no secrets, virtual environments, node_modules, local databases, or personal financial records are being committed. Suggest a clear commit message for the completed phase, but do not push to a remote without my request.
```

---

## Core API checklist

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| POST | `/api/businesses` | Business onboarding |
| GET | `/api/businesses` | Business list |
| GET | `/api/businesses/{id}` | Business profile |
| POST | `/api/businesses/{id}/imports/transactions` | Upload transactions CSV |
| POST | `/api/businesses/{id}/imports/invoices` | Upload invoices CSV |
| GET | `/api/businesses/{id}/sources` | Data provenance |
| GET | `/api/businesses/{id}/evidence-dna` | Evidence quality |
| GET | `/api/businesses/{id}/trust-graph` | Graph and findings |
| GET | `/api/businesses/{id}/financial-summary` | Financial metrics |
| POST | `/api/businesses/{id}/assess` | Create review snapshot |
| POST | `/api/businesses/{id}/stress-tests` | CashFlow Twin scenarios |
| POST | `/api/businesses/{id}/loan-options` | Illustrative loan options |
| GET | `/api/businesses/{id}/credit-passport` | Evidence-backed assessment |

---

## Suggested build order for a tight hackathon

**MVP — must work:**

- Scaffold and synthetic seed data (00–02)
- Import and reconcile records (03–04)
- Interactive, clickable Trust Graph (05)
- Financial health calculations (06)
- Stress scenarios and EMI comparison (08–09)
- Credit Passport with human review disclaimer (10)
- Integration tests and demo story (14–15)

**Enhance after MVP:** rules-based risk indicators (07), detailed review workflow (11), polished UI (12), optional ML demonstration (13), repository cleanup (16).

**Important dependency note:** Prompt 10 can include a basic placeholder for risk indicators if Prompt 07 is deferred; the placeholder must be explicitly marked **“not assessed”**, never an invented score.

## Demo differentiator: Twin Business Challenge

Two fictional shopkeepers report the *same* ₹1 lakh/month revenue and request the *same* ₹2 lakh loan. Their **verified or corroborated records differ**. CREDWEAVE AI makes that difference visible without treating missing documents as proof of fraud or assuming that evidence quality equals repayment probability. Then judges apply a 20% sales decline and compare four loan tenures before viewing the Credit Passports.

### Final one-sentence pitch

> **“Traditional lending asks: What's your credit score? CREDWEAVE AI asks: What can your business actually demonstrate?”**

---

## Definition of done

A judge can open the application, choose two synthetic merchants, see documented financial and evidence indicators, inspect the Trust Graph and its source records, run a scenario, compare EMIs, and export or print an honest, traceable Credit Passport—all without requiring real financial accounts or claiming automated approval.
