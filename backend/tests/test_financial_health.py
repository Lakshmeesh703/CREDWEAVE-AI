from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.services.financial_health import calculate_financial_health


def transaction(identifier, day, amount, direction, description="operating"):
    return SimpleNamespace(
        id=identifier,
        transaction_date=date(2025, 7, day),
        amount_inr=Decimal(str(amount)),
        direction=SimpleNamespace(value=direction),
        description=description,
    )


def test_hand_worked_cash_flow_excludes_internal_transfer_and_refund():
    result = calculate_financial_health(
        transactions=[
            transaction("credit", 1, 100000, "credit"),
            transaction("supplier", 2, 40000, "debit"),
            transaction("transfer", 3, 25000, "credit", "internal transfer between own accounts"),
            transaction("refund", 4, 5000, "credit", "customer refund received"),
        ],
        obligations=[SimpleNamespace(monthly_payment_inr=Decimal("10000"))],
        supplier_concentration_percent="80.00",
    )

    assert result["monthly"] == [{
        "month": "2025-07",
        "inflows_inr": "100000.00",
        "outflows_inr": "40000.00",
        "net_cash_flow_inr": "60000.00",
        "positive_net_month": True,
    }]
    assert result["metrics"]["total_inflows"]["value"] == "100000.00"
    assert result["metrics"]["net_operating_cash_flow"]["value"] == "60000.00"
    assert result["metrics"]["monthly_debt_obligations"]["value"] == "10000.00"
    assert result["coverage"]["excluded_transaction_count"] == 2
    assert result["seasonality"]["label"] == "insufficient_history"


def test_sparse_negative_cash_flow_month_is_preserved():
    result = calculate_financial_health(
        transactions=[
            transaction("credit", 1, 100, "credit"),
            transaction("debit", 20, 250, "debit"),
        ],
        obligations=[SimpleNamespace(monthly_payment_inr=Decimal("50"))],
        supplier_concentration_percent="100.00",
    )

    assert result["monthly"][0]["net_cash_flow_inr"] == "-150.00"
    assert result["monthly"][0]["positive_net_month"] is False
    assert result["metrics"]["negative_months"]["value"] == 1
    assert result["seasonality"]["observed_months"] == 1


def test_zero_inflows_do_not_create_infinite_ratio_or_growth():
    result = calculate_financial_health(
        transactions=[transaction("debit", 1, 100, "debit")],
        obligations=[],
    )

    assert result["metrics"]["expense_to_inflow_ratio"]["value"] is None
    assert result["metrics"]["revenue_growth"]["value"] is None
    assert result["metrics"]["negative_months"]["value"] == 1
