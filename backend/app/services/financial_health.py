from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from statistics import pstdev
from typing import Any, Iterable

FINANCIAL_RULE_VERSION = "financial-health.v1"
_NON_OPERATING_MARKERS = ("internal transfer", "self transfer", "refund")


def _money(value: Decimal | int | float) -> str:
    return f"{Decimal(str(value)).quantize(Decimal('0.01'))}"


def _month(value: date) -> str:
    return value.strftime("%Y-%m")


def _enum_value(value: Any) -> str:
    return getattr(value, "value", value)


def _is_non_operating(transaction: Any) -> bool:
    description = (transaction.description or "").casefold()
    return any(marker in description for marker in _NON_OPERATING_MARKERS)


def supplier_concentration_percent(transactions: Iterable[Any], counterparties: Iterable[Any]) -> str | None:
    supplier_ids = {
        item.id
        for item in counterparties
        if getattr(item.type, "value", item.type) == "supplier"
    }
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for transaction in transactions:
        if (
            _enum_value(transaction.direction) == "debit"
            and transaction.counterparty_id in supplier_ids
            and not _is_non_operating(transaction)
        ):
            totals[transaction.counterparty_id] += abs(Decimal(str(transaction.amount_inr)))
    total = sum(totals.values(), Decimal("0"))
    if not total:
        return None
    return _money(max(totals.values()) / total * Decimal("100"))


def _metric(
    value: str | int | float | None,
    *,
    unit: str,
    formula: str,
    data_coverage: str,
    caveats: list[str],
) -> dict[str, Any]:
    return {
        "value": value,
        "unit": unit,
        "formula": formula,
        "data_coverage": data_coverage,
        "caveats": caveats,
    }


def calculate_financial_health(
    *,
    transactions: Iterable[Any],
    obligations: Iterable[Any],
    supplier_concentration_percent: str | None = None,
) -> dict[str, Any]:
    """Calculate deterministic cash-flow indicators from normalized records.

    Invoice totals are intentionally not used for cash-flow totals. Credits and
    debits marked as internal transfers or refunds are excluded from operating
    flows and surfaced in the coverage metadata.
    """
    transaction_list = sorted(transactions, key=lambda item: (item.transaction_date, item.id))
    obligation_list = list(obligations)
    if not transaction_list:
        return _empty_result(obligation_list, supplier_concentration_percent)

    monthly: dict[str, dict[str, Decimal | int]] = defaultdict(
        lambda: {"inflows": Decimal("0"), "outflows": Decimal("0"), "positive": 0, "negative": 0}
    )
    excluded_count = 0
    excluded_amount = Decimal("0")
    operating_inflow = Decimal("0")
    operating_outflow = Decimal("0")
    for transaction in transaction_list:
        amount = abs(Decimal(str(transaction.amount_inr)))
        if _is_non_operating(transaction):
            excluded_count += 1
            excluded_amount += amount
            continue
        bucket = monthly[_month(transaction.transaction_date)]
        if _enum_value(transaction.direction) == "credit":
            bucket["inflows"] += amount
            operating_inflow += amount
        else:
            bucket["outflows"] += amount
            operating_outflow += amount

    months = []
    for month_name in sorted(monthly):
        bucket = monthly[month_name]
        net = bucket["inflows"] - bucket["outflows"]
        bucket["positive"] = int(net > 0)
        bucket["negative"] = int(net < 0)
        months.append(
            {
                "month": month_name,
                "inflows_inr": _money(bucket["inflows"]),
                "outflows_inr": _money(bucket["outflows"]),
                "net_cash_flow_inr": _money(net),
                "positive_net_month": net > 0,
            }
        )

    net_values = [Decimal(item["net_cash_flow_inr"]) for item in months]
    inflow_values = [Decimal(item["inflows_inr"]) for item in months if Decimal(item["inflows_inr"]) > 0]
    expense_ratio = (
        operating_outflow / operating_inflow * Decimal("100")
        if operating_inflow
        else None
    )
    volatility = pstdev(net_values) if len(net_values) > 1 else None
    revenue_growth = None
    revenue_growth_caveat = "At least two months with operating inflows are required."
    if len(inflow_values) >= 2 and inflow_values[0]:
        revenue_growth = (inflow_values[-1] - inflow_values[0]) / inflow_values[0] * Decimal("100")
        revenue_growth_caveat = "Operating inflow is used as a cash receipt proxy; it is not accounting revenue."

    total_obligation = sum(
        (Decimal(str(item.monthly_payment_inr)) for item in obligation_list),
        Decimal("0"),
    )
    date_window = f"{transaction_list[0].transaction_date.isoformat()} to {transaction_list[-1].transaction_date.isoformat()}"
    coverage = (
        f"{len(months)} calendar months with transactions; "
        f"{excluded_count} non-operating records excluded from operating totals."
    )
    caveats = [
        "Net cash flow is not accounting profit and excludes invoice totals.",
        "Missing records are unknown evidence; this calculation does not impute absent transactions.",
    ]
    return {
        "rule_version": FINANCIAL_RULE_VERSION,
        "date_window": {"start": transaction_list[0].transaction_date.isoformat(), "end": transaction_list[-1].transaction_date.isoformat()},
        "monthly": months,
        "metrics": {
            "total_inflows": _metric(_money(operating_inflow), unit="INR", formula="sum eligible credit transactions", data_coverage=coverage, caveats=caveats),
            "total_outflows": _metric(_money(operating_outflow), unit="INR", formula="sum eligible debit transactions", data_coverage=coverage, caveats=caveats),
            "net_operating_cash_flow": _metric(_money(operating_inflow - operating_outflow), unit="INR", formula="eligible inflows - eligible outflows", data_coverage=coverage, caveats=caveats),
            "expense_to_inflow_ratio": _metric(_money(expense_ratio) if expense_ratio is not None else None, unit="percent", formula="eligible outflows / eligible inflows * 100", data_coverage=coverage, caveats=["Undefined when eligible inflows are zero."]),
            "cash_flow_volatility": _metric(_money(volatility) if volatility is not None else None, unit="INR standard deviation", formula="population standard deviation of monthly net cash flow", data_coverage=coverage, caveats=["Undefined with fewer than two months."]),
            "positive_months": _metric(sum(item["positive_net_month"] for item in months), unit="months", formula="count months where net cash flow > 0", data_coverage=coverage, caveats=[]),
            "negative_months": _metric(sum(not item["positive_net_month"] for item in months), unit="months", formula="count months where net cash flow <= 0", data_coverage=coverage, caveats=[]),
            "revenue_growth": _metric(_money(revenue_growth) if revenue_growth is not None else None, unit="percent", formula="(last eligible monthly inflow - first eligible monthly inflow) / first eligible monthly inflow * 100", data_coverage=coverage, caveats=[revenue_growth_caveat]),
            "supplier_concentration": _metric(supplier_concentration_percent, unit="percent of supplier debit spend", formula="top supplier debit spend / total supplier debit spend * 100", data_coverage="Derived from business-scoped supplier-linked debit transactions.", caveats=["Not a default-risk score. Undefined when supplier-linked debit spend is zero."]),
            "monthly_debt_obligations": _metric(_money(total_obligation), unit="INR per month", formula="sum obligation.monthly_payment_inr", data_coverage=f"{len(obligation_list)} obligation records", caveats=["Obligation records may be incomplete or stale."]),
        },
        "seasonality": {
            "label": "insufficient_history" if len(months) < 12 else "observed",
            "method": "Compare monthly operating inflow and net cash flow patterns; no seasonal conclusion is made below 12 months.",
            "observed_months": len(months),
            "warning": "At least 12 months of operating history are needed before assessing seasonality." if len(months) < 12 else None,
        },
        "coverage": {
            "transaction_count": len(transaction_list),
            "operating_transaction_count": len(transaction_list) - excluded_count,
            "excluded_transaction_count": excluded_count,
            "excluded_amount_inr": _money(excluded_amount),
            "date_window": date_window,
        },
        "limitations": [
            "No ML default-risk score or automatic lending decision is produced.",
            "Revenue growth uses eligible cash inflow as a proxy only when the source definition does not support accounting revenue.",
            "Internal transfers and refunds are detected from normalized descriptions; ambiguous records require human review.",
        ],
    }


def _empty_result(obligations: Iterable[Any], supplier_concentration_percent: str | None) -> dict[str, Any]:
    total_obligation = sum((Decimal(str(item.monthly_payment_inr)) for item in obligations), Decimal("0"))
    empty = _metric("0.00", unit="INR", formula="no eligible transactions", data_coverage="0 transactions", caveats=["No transaction data is available."])
    return {
        "rule_version": FINANCIAL_RULE_VERSION,
        "date_window": {"start": None, "end": None},
        "monthly": [],
        "metrics": {
            "total_inflows": empty,
            "total_outflows": empty,
            "net_operating_cash_flow": empty,
            "expense_to_inflow_ratio": _metric(None, unit="percent", formula="eligible outflows / eligible inflows * 100", data_coverage="0 transactions", caveats=["Undefined when eligible inflows are zero."]),
            "cash_flow_volatility": _metric(None, unit="INR standard deviation", formula="population standard deviation of monthly net cash flow", data_coverage="0 months", caveats=["Undefined with fewer than two months."]),
            "positive_months": _metric(0, unit="months", formula="count months where net cash flow > 0", data_coverage="0 months", caveats=[]),
            "negative_months": _metric(0, unit="months", formula="count months where net cash flow <= 0", data_coverage="0 months", caveats=[]),
            "revenue_growth": _metric(None, unit="percent", formula="cash inflow proxy growth", data_coverage="0 months", caveats=["At least two months with operating inflows are required."]),
            "supplier_concentration": _metric(supplier_concentration_percent, unit="percent of supplier debit spend", formula="top supplier debit spend / total supplier debit spend * 100", data_coverage="No supplier-linked debit transactions.", caveats=[]),
            "monthly_debt_obligations": _metric(_money(total_obligation), unit="INR per month", formula="sum obligation.monthly_payment_inr", data_coverage="obligation records", caveats=[]),
        },
        "seasonality": {"label": "insufficient_history", "method": "No seasonality conclusion without transaction months.", "observed_months": 0, "warning": "No transaction history is available."},
        "coverage": {"transaction_count": 0, "operating_transaction_count": 0, "excluded_transaction_count": 0, "excluded_amount_inr": "0.00", "date_window": None},
        "limitations": ["No transaction data is available; metrics must not be interpreted as evidence of low risk."],
    }
