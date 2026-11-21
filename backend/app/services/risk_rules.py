from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.financial_health import FINANCIAL_RULE_VERSION

THRESHOLDS_PATH = Path(__file__).parents[1] / "config" / "risk_thresholds.json"


def load_risk_thresholds() -> dict[str, Any]:
    return json.loads(THRESHOLDS_PATH.read_text(encoding="utf-8"))


def _number(metrics: dict[str, Any], name: str) -> float | None:
    value = metrics[name]["value"]
    return float(value) if value is not None else None


def evaluate_rules(financial: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    config = load_risk_thresholds()
    thresholds = config["thresholds"]
    metrics = financial["metrics"]
    average_inflow = sum(float(item["inflows_inr"]) for item in financial["monthly"]) / len(financial["monthly"]) if financial["monthly"] else 0
    debt = _number(metrics, "monthly_debt_obligations") or 0
    debt_burden = debt / average_inflow * 100 if average_inflow else None
    volatility = _number(metrics, "cash_flow_volatility")
    volatility_ratio = volatility / average_inflow * 100 if volatility is not None and average_inflow else None
    values = {
        "expense_to_inflow_ratio_percent": _number(metrics, "expense_to_inflow_ratio"),
        "debt_to_average_inflow_percent": debt_burden,
        "negative_months": _number(metrics, "negative_months"),
        "volatility_to_average_inflow_percent": volatility_ratio,
        "supplier_concentration_percent": _number(metrics, "supplier_concentration"),
    }
    indicators: list[dict[str, Any]] = []
    key_risk_factors: list[str] = []
    mitigating_factors: list[str] = []
    for name, value in values.items():
        threshold = thresholds[name]
        if value is None:
            status = "unknown"
            explanation = "The available evidence cannot support this indicator."
            key_risk_factors.append(f"{name} is unknown")
        elif value >= threshold["elevated"]:
            status = "elevated"
            explanation = f"{value:.2f} meets or exceeds the elevated review threshold of {threshold['elevated']}."
            key_risk_factors.append(f"{name} is elevated")
        elif value >= threshold["watch"]:
            status = "watch"
            explanation = f"{value:.2f} meets or exceeds the watch threshold of {threshold['watch']}."
            key_risk_factors.append(f"{name} warrants review")
        else:
            status = "within_rule_range"
            explanation = f"{value:.2f} is below the watch threshold of {threshold['watch']}."
            mitigating_factors.append(f"{name} is below the watch threshold")
        indicators.append({
            "code": name,
            "status": status,
            "value": round(value, 2) if value is not None else None,
            "unit": "percent" if "percent" in name else "months",
            "thresholds": threshold,
            "explanation": explanation,
            "formula": {
                "debt_to_average_inflow_percent": "monthly obligations / average monthly eligible inflow * 100",
                "volatility_to_average_inflow_percent": "monthly net cash-flow population standard deviation / average monthly eligible inflow * 100",
            }.get(name, f"financial-summary metric: {name}"),
        })

    evidence_quality = {
        "completeness": evidence["evidence_completeness"],
        "consistency": evidence["evidence_consistency"],
        "verification_status": evidence["verification_status"],
        "limitations": evidence["limitations"],
    }
    confidence = evidence["assessment_confidence"]
    unknowns = [
        "No validated probability of default is estimated; repayment outcome labels are not available.",
        *[item["explanation"] for item in indicators if item["status"] == "unknown"],
    ]
    questions = [
        "Which unknown or elevated indicator can the business substantiate with additional source records?",
        "Are the listed monthly obligations complete and current?",
        "Can the reviewer confirm whether high supplier concentration reflects a stable contractual relationship?",
    ]
    return {
        "rule_version": config["rule_version"],
        "financial_rule_version": FINANCIAL_RULE_VERSION,
        "risk_indicators": indicators,
        "evidence_quality": evidence_quality,
        "assessment_confidence": {
            "label": confidence["label"],
            "rationale": confidence["rationale"],
            "derivation": "Inherited from evidence coverage and reconciliation quality; independent of the financial risk indicators.",
        },
        "key_risk_factors": key_risk_factors,
        "mitigating_factors": mitigating_factors,
        "unknowns": unknowns,
        "recommended_lender_questions": questions,
        "decision_boundary": "Rules-only decision support. This output does not estimate default likelihood and must not automatically accept or reject credit.",
        "fairness_notes": [
            "Rules use transaction behavior and evidence coverage only; protected traits are not used.",
            "Evidence coverage can reflect access barriers or record availability and must not be treated as character or repayment evidence.",
            "A human reviewer should investigate context before drawing conclusions from any indicator.",
        ],
        "thresholds": thresholds,
    }
