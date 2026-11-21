# Synthetic-only ML method evaluation

## Data availability decision

CREDWEAVE AI has **no defensible repayment-prediction training data**. The repository contains synthetic business evidence only, with no consented, ethically licensed, documented, real-world repayment outcomes and no known outcome provenance. Supervised default-risk training is therefore intentionally not implemented or exposed through the application.

The rules-only pipeline remains the production fallback for this prototype.

## Synthetic method demonstration

`backend/app/ml/synthetic_method_demo.py` is an isolated reproducibility demonstration. It generates in-memory synthetic financial features and artificial labels from a fixed seed. It does not read or write real business records.

### Generated features

- Expense-to-inflow ratio
- Debt-to-average-inflow ratio
- Negative cash-flow month count
- Cash-flow volatility
- Supplier concentration
- Average monthly net cash

The demonstration excludes evidence verification status, protected traits, real identities, and real repayment outcomes.

### Split and model

- Fixed seed: `2026`
- Entity holdout: the last synthetic entity
- Train rows: 300
- Test rows: 100
- Baseline: standardized Logistic Regression
- Metrics: ROC-AUC when both classes are present, PR-AUC, Brier score, confusion matrix
- Uncertainty and feature influence: held-out metrics and standardized coefficients

The held-out entity may differ from real-world population behavior. No calibration, uncertainty interval, fairness result, or subgroup conclusion is suitable for lending use.

## Ethical and operational limitations

- Artificial labels do not represent repayment behavior.
- Reported metrics are not validation of real credit risk.
- The demonstration is not a probability-of-default model.
- It must not be shown in a lender-facing decision screen.
- It must not be used for approval, denial, pricing, or eligibility decisions.
- Evidence verification status is excluded because this prototype has not demonstrated that evidence status is a valid or fair predictor of repayment.
- Any future real-world experiment would require documented consent/licensing, known label provenance, entity/time validation, leakage audit, subgroup fairness assessment with lawful support, governance, monitoring, and human approval.

## Run

```bash
cd backend
source .venv/bin/activate
python -m app.ml.synthetic_method_demo
```

Optional machine-readable report:

```python
from app.ml.synthetic_method_demo import write_report
write_report("../docs/generated_synthetic_ml_demo.json")
```

The generated report must remain labeled as synthetic and must never be described as real-world model performance.
