from __future__ import annotations

from decimal import Decimal, ROUND_CEILING
from typing import Any, Sequence

STRESS_RULE_VERSION = "cashflow-twin.v1"


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _money(value: Decimal | int | float | str) -> str:
    return str(Decimal(str(value)).quantize(Decimal("0.01")))


def _delay_months(days: int) -> int:
    return int((Decimal(days) / Decimal("30")).to_integral_value(rounding=ROUND_CEILING))


def calculate_stress_test(
    *,
    base_monthly: Sequence[dict[str, Any]],
    revenue_shock_pct: Decimal,
    expense_shock_pct: Decimal,
    payment_delay_days: int,
    duration_months: int,
    selected_loan_emi: Decimal,
    seasonal_weaker_months: int = 0,
) -> dict[str, Any]:
    if not base_monthly:
        raise ValueError("At least one base month is required.")
    delay_months = _delay_months(payment_delay_days)
    projected: list[dict[str, Any]] = []
    delayed_beyond_horizon = Decimal("0")
    for index in range(duration_months):
        source = base_monthly[index % len(base_monthly)]
        base_inflow = _decimal(source["inflows_inr"])
        base_outflow = _decimal(source["outflows_inr"])
        shocked_inflow = base_inflow * (Decimal("1") + revenue_shock_pct / Decimal("100"))
        shocked_outflow = base_outflow * (Decimal("1") + expense_shock_pct / Decimal("100"))
        if index < seasonal_weaker_months:
            shocked_inflow *= Decimal("0.80")
        # A delay shifts cash timing, rather than reducing total customer receipts.
        arrived_inflow = Decimal("0")
        if index >= delay_months:
            delayed_source = base_monthly[(index - delay_months) % len(base_monthly)]
            arrived_inflow = _decimal(delayed_source["inflows_inr"]) * (Decimal("1") + revenue_shock_pct / Decimal("100"))
            if index - delay_months < seasonal_weaker_months:
                arrived_inflow *= Decimal("0.80")
        elif delay_months == 0:
            arrived_inflow = shocked_inflow
        if delay_months and index + delay_months >= duration_months:
            delayed_beyond_horizon += shocked_inflow
        net_before_emi = arrived_inflow - shocked_outflow
        net_after_emi = net_before_emi - selected_loan_emi
        coverage = arrived_inflow / selected_loan_emi if selected_loan_emi > 0 else None
        projected.append({
            "month_number": index + 1,
            "label": str(source.get("month", f"Month {index + 1}")),
            "base_inflows_inr": _money(base_inflow),
            "base_outflows_inr": _money(base_outflow),
            "projected_inflows_inr": _money(arrived_inflow),
            "projected_outflows_inr": _money(shocked_outflow),
            "net_cash_before_emi_inr": _money(net_before_emi),
            "loan_emi_inr": _money(selected_loan_emi),
            "net_cash_after_emi_inr": _money(net_after_emi),
            "emi_coverage_ratio": _money(coverage) if coverage is not None else None,
            "cash_gap_inr": _money(max(Decimal("0"), -net_after_emi)),
        })
    minimum_after_emi = min((_decimal(item["net_cash_after_emi_inr"]) for item in projected), default=Decimal("0"))
    total_base_inflow = sum((_decimal(item["inflows_inr"]) for item in base_monthly), Decimal("0"))
    total_projected_inflow = sum((_decimal(item["projected_inflows_inr"]) for item in projected), Decimal("0"))
    warnings = [
        "Scenario outputs are deterministic illustrations, not guaranteed forecasts.",
        "Payment delay uses a 30-day monthly timing approximation and preserves delayed receipts.",
    ]
    if delayed_beyond_horizon:
        warnings.append(f"{_money(delayed_beyond_horizon)} of modeled receipts arrive after the selected horizon.")
    if len(base_monthly) < 12:
        warnings.append("Observed history is shorter than 12 months; seasonality and projections are uncertain.")
    if minimum_after_emi < 0:
        warnings.append("At least one projected month has a cash gap after the selected EMI.")
    return {
        "rule_version": STRESS_RULE_VERSION,
        "scenario": {
            "revenue_shock_pct": _money(revenue_shock_pct),
            "expense_shock_pct": _money(expense_shock_pct),
            "payment_delay_days": payment_delay_days,
            "payment_delay_months": delay_months,
            "duration_months": duration_months,
            "selected_loan_emi_inr": _money(selected_loan_emi),
            "seasonal_weaker_months": seasonal_weaker_months,
        },
        "monthly": projected,
        "metrics": {
            "minimum_net_cash_after_emi_inr": _money(minimum_after_emi),
            "minimum_liquidity_or_cash_gap_inr": _money(minimum_after_emi),
            "total_base_inflows_inr": _money(total_base_inflow),
            "total_projected_inflows_inr": _money(total_projected_inflow),
            "receipts_delayed_beyond_horizon_inr": _money(delayed_beyond_horizon),
            "cash_conservation_note": "Payment delays shift receipt timing; they do not delete modeled customer receipts.",
        },
        "warnings": warnings,
        "assumptions": [
            "Base months repeat cyclically when duration exceeds observed history.",
            "Revenue shocks apply to customer inflows; expense shocks apply to recorded outflows.",
            "The selected EMI is paid monthly at the end of each modeled month.",
        ],
    }


PRESETS = {
    "normal": {"label": "Normal operations", "revenue_shock_pct": 0, "expense_shock_pct": 0, "payment_delay_days": 0, "seasonal_weaker_months": 0},
    "sales_decline": {"label": "Sales decline", "revenue_shock_pct": -20, "expense_shock_pct": 0, "payment_delay_days": 0, "seasonal_weaker_months": 0},
    "supplier_cost_increase": {"label": "Supplier cost increase", "revenue_shock_pct": 0, "expense_shock_pct": 15, "payment_delay_days": 0, "seasonal_weaker_months": 0},
    "seasonal_disruption": {"label": "Seasonal disruption", "revenue_shock_pct": 0, "expense_shock_pct": 0, "payment_delay_days": 0, "seasonal_weaker_months": 2},
    "combined_crisis": {"label": "Combined crisis", "revenue_shock_pct": -20, "expense_shock_pct": 15, "payment_delay_days": 45, "seasonal_weaker_months": 2},
}
