from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP, localcontext
import json
from pathlib import Path
from typing import Any, Sequence

_THRESHOLDS = json.loads(
    (Path(__file__).parent.parent / "config" / "loan_thresholds.json").read_text()
)
LOAN_RULE_VERSION = _THRESHOLDS["rule_version"]
AFFORDABILITY_MIN_DSCR = Decimal(str(_THRESHOLDS["minimum_dscr"]))
NEGATIVE_POST_EMI_MONTHS_ALLOWED = int(_THRESHOLDS["negative_post_emi_months_allowed"])


def _money(value: Decimal | int | float | str) -> str:
    return str(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def calculate_emi(principal: Decimal, annual_rate_pct: Decimal, tenure_months: int) -> Decimal:
    if principal < 0 or annual_rate_pct < 0 or tenure_months < 1:
        raise ValueError("Principal, interest rate, and tenure must be non-negative and valid.")
    if annual_rate_pct == 0:
        return principal / Decimal(tenure_months)
    with localcontext() as context:
        context.prec = 40
        monthly_rate = annual_rate_pct / Decimal("1200")
        power = (Decimal("1") + monthly_rate) ** tenure_months
        return principal * monthly_rate * power / (power - Decimal("1"))


def build_loan_options(
    *,
    principal: Decimal,
    annual_rate_pct: Decimal,
    tenure_months: Sequence[int],
    origination_fee: Decimal,
    scenario_monthly: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    if not scenario_monthly:
        raise ValueError("At least one scenario month is required.")
    if principal <= 0:
        raise ValueError("Requested principal must be greater than zero.")
    if origination_fee < 0:
        raise ValueError("Origination fee cannot be negative.")
    options: list[dict[str, Any]] = []
    for tenure in tenure_months:
        if tenure < 1 or tenure > 120:
            raise ValueError("Tenure must be between 1 and 120 months.")
        emi = calculate_emi(principal, annual_rate_pct, tenure)
        total_repayment = emi * Decimal(tenure)
        interest_cost = total_repayment - principal
        months = []
        for item in scenario_monthly:
            inflow = Decimal(str(item["inflows_inr"]))
            outflow = Decimal(str(item["outflows_inr"]))
            available_cash = inflow - outflow
            post_emi = available_cash - emi
            dscr = available_cash / emi if emi > 0 else None
            months.append({
                "month": str(item.get("month", item.get("label", "scenario"))),
                "scenario_inflows_inr": _money(inflow),
                "scenario_outflows_inr": _money(outflow),
                "available_cash_before_new_debt_inr": _money(available_cash),
                "proposed_emi_inr": _money(emi),
                "net_cash_after_proposed_emi_inr": _money(post_emi),
                "debt_service_coverage_ratio": _money(dscr) if dscr is not None else None,
                "coverage_definition": "available cash before new debt / proposed EMI; null when EMI is zero",
            })
        negative_months = sum(Decimal(item["net_cash_after_proposed_emi_inr"]) < 0 for item in months)
        dscr_values = [Decimal(item["debt_service_coverage_ratio"]) for item in months if item["debt_service_coverage_ratio"] is not None]
        minimum_dscr = min(dscr_values) if dscr_values else None
        minimum_post_emi = min((Decimal(item["net_cash_after_proposed_emi_inr"]) for item in months), default=Decimal("0"))
        affordable = negative_months <= NEGATIVE_POST_EMI_MONTHS_ALLOWED and minimum_dscr is not None and minimum_dscr >= AFFORDABILITY_MIN_DSCR
        options.append({
            "tenure_months": tenure,
            "emi_inr": _money(emi),
            "total_repayment_inr": _money(total_repayment),
            "interest_cost_inr": _money(interest_cost),
            "origination_fee_inr": _money(origination_fee),
            "total_cost_inr": _money(total_repayment + origination_fee),
            "affordability_status": "may be affordable under the specified scenario" if affordable else "requires review",
            "affordability_rationale": (
                f"No negative post-EMI months and minimum DSCR {minimum_dscr} meets the {AFFORDABILITY_MIN_DSCR} threshold."
                if affordable
                else f"{negative_months} month(s) have negative post-EMI cash or minimum DSCR {minimum_dscr} is below {AFFORDABILITY_MIN_DSCR}."
            ),
            "minimum_post_emi_cash_inr": _money(minimum_post_emi),
            "minimum_dscr": _money(minimum_dscr) if minimum_dscr is not None else None,
            "monthly": months,
            "tradeoffs": [
                "Shorter tenure generally increases EMI and reduces total interest.",
                "Longer tenure generally lowers EMI but increases total interest.",
                "This is an illustrative scenario comparison and not an eligibility or approval decision.",
            ],
        })
    return {
        "rule_version": LOAN_RULE_VERSION,
        "requested_principal_inr": _money(principal),
        "annual_interest_rate_pct": _money(annual_rate_pct),
        "origination_fee_inr": _money(origination_fee),
        "thresholds": {"minimum_dscr": _money(AFFORDABILITY_MIN_DSCR), "negative_post_emi_months_allowed": NEGATIVE_POST_EMI_MONTHS_ALLOWED},
        "options": options,
        "assumptions": [
            "Interest uses monthly compounding with annual rate divided by 12.",
            "Origination fee is disclosed separately and included in total cost.",
            "Available cash is scenario inflows minus scenario outflows; accounting profit is not inferred.",
            "Missing evidence is not treated as a risk outcome; scenario coverage and limitations require lender review.",
        ],
    }
