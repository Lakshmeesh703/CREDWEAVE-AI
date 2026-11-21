# CREDWEAVE AI Implementation Plan

**Date:** 2026-11-20  
**Prototype:** Finance F2 - Credit for the Credit-Invisible  
**Status:** The planned hackathon prototype has been implemented. This document records the original scope; see [FEATURE_STATUS.md](FEATURE_STATUS.md) and [ARCHITECTURE.md](ARCHITECTURE.md) for the current implementation.

## 1. Product Scope

CREDWEAVE AI is a local, hackathon-ready decision-support prototype for a human lender reviewing a small business with limited formal credit history. It reconciles synthetic records from multiple sources, exposes evidence quality and consistency separately from financial risk, builds an explainable business trust graph, runs deterministic financial and stress calculations, and produces illustrative loan options.

The system does **not** make an automatic approval or denial decision. Every assessment is a decision aid for a human reviewer and must show assumptions, uncertainty, limitations, consent status, and the rule/model version used.

## 2. Architecture

```text
React + Vite + TypeScript UI
  - Onboarding, Evidence DNA, Trust Graph, financial/risk screens
  - CashFlow Twin, loan options, passport, reviewer desk
             |
             | JSON / multipart REST
             v
FastAPI + Pydantic
  - API validation and orchestration
             |
             v
Deterministic services
  - Evidence DNA, NetworkX graph, pandas financial metrics
  - Rule-based assessment, scenario engine, EMI calculation
             |
             v
SQLAlchemy 2 -> explicitly configured Supabase PostgreSQL

pytest -> isolated in-memory SQLite (tests only)
```

### Architectural boundaries

- **Frontend:** presentation, local UI state, API client, chart/graph rendering, and reviewer workflow. It must not duplicate financial calculations.
- **API layer:** Supabase session verification, ownership and lender consent, schema validation, and orchestration. Domain calculation code remains in the services.
- **Domain services:** deterministic calculations and explanations. Each service returns values, inputs, assumptions, warnings, and a version identifier.
- **Persistence:** SQLAlchemy models and sessions. Development uses configured Supabase/PostgreSQL, jury mode provisions a temporary SQLite file, and tests use isolated in-memory SQLite.
- **Synthetic data:** fixtures and import adapters are clearly marked `SYNTHETIC`; simulated bank/UPI sources are never presented as live integrations.

## 3. Module Boundaries

### Backend

```text
backend/app/
  api/          # HTTP routers, dependency wiring, error mapping
  core/         # settings, versioning, consent/privacy helpers
  db/           # engine, session, migrations/initialization
  models/       # SQLAlchemy persistence models
  schemas/      # Pydantic request/response contracts
  repositories/ # database access and query composition
  services/     # evidence, graph, metrics, risk, stress, loan, passport
  fixtures/     # synthetic seed data only
backend/tests/
```

### Frontend

```text
frontend/src/
  app/          # routing, providers, app shell
  components/   # reusable UI and status indicators
  features/     # identity, evidence, graph, health, risk, cashflow, loans, passport
  lib/          # typed API client, formatters, error handling
  types/        # API/domain types
```

The frontend feature modules consume typed API responses and render independently. Shared risk labels, evidence labels, INR formatting, and status semantics belong in shared utilities rather than feature-specific copies.

## 4. Data Flows

### Applicant review flow

1. Select a synthetic business profile and confirm the displayed consent status.
2. Load source records with source type, period, masked identifiers, and provenance.
3. Normalize records into common transaction/invoice/payment shapes.
4. Reconcile candidate records and classify relationships as matched, unmatched, conflicting, or unknown.
5. Build the trust graph from businesses, people/roles, invoices, payments, suppliers, and customers.
6. Calculate financial health metrics from available periods and label missing evidence separately.
7. Run explainable deterministic risk rules and scenarios; return factors, uncertainty, and rule version.
8. Generate illustrative loan options with amount, tenure, rate assumption, EMI, total repayment, and stress impact.
9. Assemble a credit passport and reviewer notes for human decision-making.

### Data integrity rules

- Missing records remain `unknown`; they are not converted to a negative risk signal.
- A reconciliation match means records are consistent with one another, not that the transaction is genuine.
- Every derived value includes source record IDs or an explicit reason that evidence is unavailable.
- Account identifiers are masked before API responses and UI display.
- Synthetic data labels appear in seed data, API metadata, and the UI.

## 5. Prioritized Milestones

### M0 - Documentation and guardrails

- Deliver this plan, decisions, API contract, README, repository ignore rules, and environment example.
- Confirm boundaries, synthetic-data policy, and deterministic calculation policy.

### M1 - Application scaffold and health check (P0) — implemented

- Create frontend and backend projects.
- Add configuration, development CORS, PostgreSQL setup, and `/api/health`.
- Add a landing screen and backend smoke test.

### M2 - Synthetic business identity and source ingestion (P0)

- Add business profile, consent status, source metadata, and normalized record models.
- Seed at least one clearly synthetic Indian small-business scenario.
- Add import validation and provenance display.

### M3 - Evidence DNA and reconciliation (P0)

- Implement deterministic matching for invoices, payments, and bank/UPI-like records.
- Expose match status, evidence completeness, consistency, verification status, and assessment confidence as separate fields.
- Add conflict and unknown cases to fixtures and tests.

### M4 - Trust graph and financial health (P0)

- Build a NetworkX-backed graph response with explainable nodes and edges.
- Calculate revenue, expense, cash balance, collection timing, concentration, and coverage metrics using pandas.
- Render graph and charts in the review workspace.

### M5 - Risk intelligence and CashFlow Twin (P0)

- Implement versioned deterministic risk factors and scenario assumptions.
- Model stress cases such as revenue decline, delayed collections, and expense increase.
- Show warnings and limitations rather than implying model certainty.

### M6 - Adaptive loan structuring and credit passport (P0)

- Generate illustrative options using correct EMI calculations.
- Produce a printable/exportable passport summary with evidence, metrics, risks, scenarios, assumptions, and human-review state.
- Add reviewer notes and explicit recommendation disclaimer.

### M7 - Demo hardening (P1)

- Add frontend accessibility and error states, API contract tests, fixture reset, and focused unit tests.
- Validate the complete demo path on a developer laptop.
- Document known limitations and demo script.

### M8 - Optional extensions (P2)

- Additional synthetic scenarios, richer graph filtering, CSV import, and optional model comparison.
- Do not add ML, cloud services, queues, Redis, Kafka, or Docker until the local deterministic demo is stable.

## 6. User Journeys

### Journey A: Lender reviews an applicant (P0)

The lender selects a synthetic business, sees identity and consent status, and opens a review workspace. They can distinguish missing evidence from contradictory evidence and understand the provenance of each displayed result.

### Journey B: Lender reconciles fragmented records (P0)

The lender inspects invoice/payment matches, unmatched records, and conflicts. The UI explains that consistency is not proof of genuineness and never labels unknown records as fraud.

### Journey C: Lender explores business relationships and health (P0)

The lender explores the trust graph and financial charts, filters by period/source, and sees the inputs and limitations for each metric.

### Journey D: Lender stress-tests repayment capacity (P0)

The lender changes a revenue, collection-delay, or expense scenario and compares cash-flow impact, coverage, and illustrative loan options. EMI and total repayment are visible in INR.

### Journey E: Lender exports a transparent review summary (P0)

The lender views a credit passport containing evidence, consistency, verification, confidence, risk factors, scenarios, assumptions, rule version, and a human-review disclaimer. No automatic decision is emitted.

## 7. Canonical Backend API Contract (Proposed)

All endpoints are prefixed with `/api`, return JSON, and include `schema_version` and `synthetic: true` in assessment-oriented responses. Errors use:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable message",
    "details": {}
  }
}
```

### Health and metadata

- `GET /api/health` -> service status, API version, environment, and synthetic-demo mode.
- `GET /api/meta/rules` -> active deterministic rule/calculation versions and limitations.

### Businesses and source data

- `GET /api/businesses?status=synthetic` -> paginated business summaries.
- `GET /api/businesses/{business_id}` -> identity, industry, location at coarse granularity, consent status, and synthetic-data label.
- `GET /api/businesses/{business_id}/sources` -> source metadata and coverage periods; no raw secrets or unmasked account IDs.
- `GET /api/businesses/{business_id}/records` -> normalized records with provenance and masked identifiers.

### Evidence and graph

- `GET /api/businesses/{business_id}/evidence` -> reconciliation groups with `match_status`, `evidence_completeness`, `evidence_consistency`, `verification_status`, and `assessment_confidence`.
- `GET /api/businesses/{business_id}/graph` -> nodes, edges, relationship explanations, and graph metadata.

### Assessments and scenarios

- `POST /api/businesses/{business_id}/assessments` -> create a deterministic assessment snapshot.
- `GET /api/assessments/{assessment_id}` -> complete assessment with inputs, metrics, risk factors, warnings, assumptions, and version metadata.
- `POST /api/assessments/{assessment_id}/scenarios` -> run a named scenario with validated parameters.
- `GET /api/assessments/{assessment_id}/scenarios` -> list scenario results.

### Loan options and review

- `POST /api/assessments/{assessment_id}/loan-options` -> generate illustrative options from explicit assumptions.
- `GET /api/assessments/{assessment_id}/loan-options` -> list options and repayment calculations.
- `GET /api/assessments/{assessment_id}/passport` -> credit passport payload suitable for UI/export.
- `POST /api/assessments/{assessment_id}/review-notes` -> save a human lender note and review status.

### Contract conventions

- IDs are opaque strings; timestamps are ISO 8601 UTC.
- Monetary values use integer paise internally where practical and return INR amounts with explicit currency metadata.
- Lists are paginated once they can exceed demo-sized fixtures.
- Request schemas reject unknown or invalid scenario fields.
- Mutating endpoints do not return `approved` or `denied`; they return `illustrative`, `requires_human_review`, and explanation fields.

## 8. Acceptance Criteria

### M0 acceptance

- The four requested documents exist: implementation plan, decisions, root README, and this API proposal.
- No frontend/backend source, package manifest, virtual environment, database, or generated build artifact is created by this milestone.
- Documentation explicitly identifies all demo data as synthetic and all recommendations as human-reviewed.

### Core prototype acceptance

- A lender can complete Journey A through E locally without external services.
- At least one fixture demonstrates missing evidence, one demonstrates a conflict, and one demonstrates a consistent match.
- Evidence completeness, consistency, verification, confidence, and risk are separately visible in API and UI responses.
- Financial metrics and EMI calculations have focused tests with known expected values.
- Every assessment exposes assumptions, uncertainty, limitations, and rule/calculation versions.
- Masked identifiers and consent status are present; no real PII or secrets are committed.
- API and frontend error states are understandable and do not silently substitute success data.

## 9. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Demo data is mistaken for real validation | High | Persistent `SYNTHETIC` labels, README disclaimer, API metadata, and UI banner |
| One score hides different evidence dimensions | High | Separate typed fields and dedicated UI sections with explanations |
| Reconciliation is interpreted as transaction proof | High | Explicit wording in schemas, UI, passport, and tests |
| EMI or INR calculations are wrong | High | Central calculation service, integer/decimal-safe math, known-value tests |
| Missing data is treated as suspicious | High | `unknown` state, neutral defaults, and fixture/test coverage |
| Scope expands into infrastructure or unverified ML | Medium | M0-M7 priority gate; defer optional services until local demo works |
| Sensitive data leaks into fixtures/logs | High | Synthetic-only policy, masked identifiers, `.env` and database ignore rules |
| Graph/chart libraries slow the demo | Medium | Keep graph payload small, use deterministic fixture, and provide tabular fallback |
| Human-review boundary is lost | High | Review status and disclaimer required in passport and loan-option responses |

## 10. Definition of Done for the Prototype

The prototype is demo-ready when the P0 journeys work from seeded synthetic data, targeted backend and frontend tests pass, the API contract is implemented consistently, and a reviewer can explain every displayed result without relying on an opaque score or external service.
