"""Synthetic-only machine-learning method demonstration.

This module does not use real repayment data and is not connected to API routes,
assessment snapshots, loan options, or lender decisions. The generated labels are
artificially constructed for pipeline mechanics only.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


FEATURE_NAMES = (
    "expense_to_inflow_ratio_percent",
    "debt_to_average_inflow_percent",
    "negative_cashflow_months",
    "cashflow_volatility_percent",
    "supplier_concentration_percent",
    "average_monthly_net_cash_inr",
)


def generate_synthetic_entities(seed: int = 2026, entities: int = 4, rows_per_entity: int = 100) -> dict:
    rng = np.random.default_rng(seed)
    rows = []
    labels = []
    entity_ids = []

    for entity_index in range(entities):
        average_inflow = rng.uniform(60000, 150000)
        monthly_obligation = rng.uniform(5000, 25000)
        supplier_concentration = rng.uniform(15, 85)

        for _ in range(rows_per_entity):
            inflow = rng.normal(average_inflow, average_inflow * 0.12)
            expense_ratio = float(rng.uniform(42, 92))
            debt_burden = float(monthly_obligation / max(inflow, 1) * 100)
            negative_months = int(rng.integers(0, 4))
            volatility = float(rng.uniform(5, 45))
            concentration = float(np.clip(rng.normal(supplier_concentration, 8), 0, 100))
            net_cash = float(rng.normal(inflow * (100 - expense_ratio) / 100 - monthly_obligation, inflow * 0.08))

            features = np.array([
                expense_ratio,
                debt_burden,
                negative_months,
                volatility,
                concentration,
                net_cash,
            ])

            latent = (
                0.025 * (expense_ratio - 65)
                + 0.035 * (debt_burden - 15)
                + 0.65 * (negative_months - 1)
                + 0.018 * (volatility - 20)
                + 0.012 * (concentration - 50)
                - 0.000015 * net_cash
            )
            probability = 1 / (1 + np.exp(-latent))
            label = int(rng.random() < np.clip(probability, 0.05, 0.95))

            rows.append(features)
            labels.append(label)
            entity_ids.append(f"synthetic-entity-{entity_index + 1:02d}")

    return {
        "x": np.vstack(rows),
        "y": np.array(labels, dtype=int),
        "entity_ids": np.array(entity_ids),
    }


def run_synthetic_method_demo(seed: int = 2026) -> dict:
    data = generate_synthetic_entities(seed=seed)
    unique_entities = np.unique(data["entity_ids"])
    if len(unique_entities) < 2:
        raise ValueError("At least two synthetic entities are required for a held-out entity split.")

    test_entities = set(unique_entities[-1:])
    train_mask = np.array([entity not in test_entities for entity in data["entity_ids"]])
    test_mask = ~train_mask

    x_train, y_train = data["x"][train_mask], data["y"][train_mask]
    x_test, y_test = data["x"][test_mask], data["y"][test_mask]

    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(random_state=seed, max_iter=1000),
    )
    model.fit(x_train, y_train)
    probabilities = model.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)

    coefficients = model.named_steps["logisticregression"].coef_[0]
    coefficient_values = {
        name: round(float(value), 6)
        for name, value in zip(FEATURE_NAMES, coefficients, strict=True)
    }

    metrics: dict = {
        "roc_auc": None,
        "pr_auc": float(average_precision_score(y_test, probabilities)),
        "brier_score": float(brier_score_loss(y_test, probabilities)),
        "confusion_matrix_[[tn,fp],[fn,tp]]": confusion_matrix(y_test, predictions).tolist(),
        "test_rows": int(len(y_test)),
        "train_rows": int(len(y_train)),
        "held_out_entities": sorted(test_entities),
    }
    if len(np.unique(y_test)) > 1:
        metrics["roc_auc"] = float(roc_auc_score(y_test, probabilities))

    return {
        "dataset": "In-memory generated synthetic features and artificial labels",
        "real_world_prediction": False,
        "model_type": "LogisticRegression method demonstration",
        "entity_split": "Last synthetic entity held out; no entity appears in both train and test",
        "features": list(FEATURE_NAMES),
        "excluded_from_features": ["evidence_verification_status", "protected_traits", "real identities", "real repayment outcomes"],
        "seed": seed,
        "metrics": metrics,
        "coefficients_standardized": coefficient_values,
        "limitations": [
            "No real repayment outcome data was used.",
            "Labels are artificial and demonstrate mechanics only.",
            "Metrics are not estimates of real lending risk or model readiness.",
            "No probability of default should be displayed to a lender from this demo.",
            "The rules-based CREDWEAVE risk pipeline remains the fallback.",
        ],
    }


def write_report(output_path: str | Path, seed: int = 2026) -> dict:
    report = run_synthetic_method_demo(seed=seed)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run_synthetic_method_demo(), indent=2))
