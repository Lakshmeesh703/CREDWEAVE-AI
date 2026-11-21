# Rules-only risk intelligence limitations

CREDWEAVE AI does not train or claim a predictive default model. The Stage 6
assessment is deterministic decision support based on configured thresholds for
cash-flow variability, expense burden, obligations, negative cash-flow months,
and supplier concentration.

The output contains review indicators and explanations, not a probability of
default, creditworthiness verdict, automatic approval, or automatic denial.
Thresholds are versioned in `backend/app/config/risk_thresholds.json` and the
assessment snapshot stores the rule version used.

Evidence completeness, evidence consistency, verification status, and assessment
confidence are reported separately from financial indicators. Missing records
remain unknown evidence. Evidence coverage may reflect access barriers,
record-keeping practices, or source availability; it must not be interpreted as
character, fraud, or repayment behavior.

The prototype does not use protected traits or obvious proxies. Human reviewers
must consider context, request follow-up evidence, and document their reasoning.
Legitimate supervised credit risk prediction would require representative,
labeled repayment outcomes, leakage controls, validation across relevant
populations, monitoring, governance, and a separate model-risk process.
