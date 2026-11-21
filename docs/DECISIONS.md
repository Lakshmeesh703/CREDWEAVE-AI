# CREDWEAVE AI Design Decisions

**Date:** 2026-11-20  
**Status:** Accepted for the hackathon prototype

## D-001: Supabase PostgreSQL for application data

Use a React/Vite frontend, FastAPI backend, and explicitly configured Supabase PostgreSQL database for development data. Automated tests use in-memory SQLite. The explicit jury launcher uses a temporary SQLite file for synthetic evidence, snapshots, and reviews during a presentation session.

**Rationale:** The demo requires a persistent shared database for the selected workflow and was explicitly configured for Supabase. Requiring `DATABASE_URL` avoids silently using an unintended local database.

**Tradeoff:** Supabase-backed development depends on credentials and network access. Jury mode runs offline after dependency installation and starts a fresh synthetic session every time. Run the Supabase seed and reset commands only against the configured demo database.

## D-002: Synthetic data only

All fixtures and simulated bank/UPI records must be synthetic and visibly labeled. No real PII, credentials, or live connectors may be committed.

**Rationale:** This protects privacy and prevents demo outcomes from being represented as validated real-world credit decisions.

**Tradeoff:** Data quality, fraud prevalence, and model performance cannot be generalized to real lending portfolios.

## D-003: Deterministic rules before ML

Implement auditable rule-based calculations first. Any later model is optional and must be versioned, compared with deterministic baselines, and accompanied by limitations.

**Rationale:** Rules are easier to test and explain in a short hackathon cycle.

**Tradeoff:** The prototype may have less predictive sophistication than a trained credit model.

## D-004: Separate evidence and risk dimensions

Represent financial risk, evidence completeness, evidence consistency, verification status, and assessment confidence as separate values.

**Rationale:** These dimensions answer different questions. Combining them into one score would conceal uncertainty and make reviewer interpretation unsafe.

**Tradeoff:** The UI and API carry more fields and require clearer explanation.

## D-005: Unknown is not negative

Missing records use an explicit `unknown` state and do not automatically increase risk or indicate fraud.

**Rationale:** Credit-invisible businesses often have incomplete formal records. Penalizing missing evidence would encode an unfair assumption.

**Tradeoff:** A lender must interpret uncertainty rather than receiving a single simplified ranking.

## D-006: Reconciliation is consistency evidence

A matched invoice/payment pair indicates that records agree on selected attributes. It does not verify that the underlying transaction is genuine.

**Rationale:** Cross-source matching is useful evidence but cannot establish truth without independent verification.

**Tradeoff:** Explanations must be repeated in the evidence UI, risk output, and credit passport.

## D-007: Human lender remains the decision-maker

Loan options and risk outputs are illustrative. The API must not produce automatic approval or denial outcomes.

**Rationale:** The product is decision support, not automated underwriting.

**Tradeoff:** The demo must include a reviewer workflow and explicit review state instead of a one-click decision.

## D-008: INR and correct EMI semantics

Use INR metadata, Indian-style scenarios, and a central EMI calculation service with testable decimal-safe arithmetic.

**Rationale:** Correct local financial semantics are essential to credibility.

**Tradeoff:** Formatting and rounding rules need to be documented and consistently applied across API, charts, and passport output.

## D-009: Provenance is first-class

Derived metrics and explanations retain source record IDs, periods, assumptions, and rule/calculation versions.

**Rationale:** A lender must be able to trace a result back to its evidence and understand its limitations.

**Tradeoff:** Models, schemas, and responses are more detailed than a minimal CRUD application.

## D-010: Privacy by design

Store only minimum necessary fields, keep consent status explicit, mask account identifiers, and load configuration from environment variables.

**Rationale:** Financial records are sensitive even in a prototype.

**Tradeoff:** Debugging and demos use synthetic IDs and masked values rather than realistic account details.

## D-011: REST contract before implementation

Agree on resource names, response dimensions, error shape, version metadata, and human-review semantics before building frontend or backend modules.

**Rationale:** The frontend and backend can evolve independently without silently inventing incompatible shapes.

**Tradeoff:** Some endpoint details may be refined after the first fixture and domain-model review.

## D-012: Modular monorepo

Keep frontend and backend in separate top-level folders with domain-oriented backend services and frontend feature modules.

**Rationale:** This supports parallel work, focused tests, and clear ownership while remaining easy to run locally.

**Tradeoff:** There is more initial structure than a single-file prototype.
