from decimal import Decimal

from app.services.stress_testing import calculate_stress_test


BASE = [
    {"month": "2024-01", "inflows_inr": "1000.00", "outflows_inr": "400.00"},
    {"month": "2024-02", "inflows_inr": "1200.00", "outflows_inr": "500.00"},
]


def test_zero_shocks_match_base_model():
    result = calculate_stress_test(
        base_monthly=BASE,
        revenue_shock_pct=Decimal("0"),
        expense_shock_pct=Decimal("0"),
        payment_delay_days=0,
        duration_months=2,
        selected_loan_emi=Decimal("0"),
    )
    assert [item["projected_inflows_inr"] for item in result["monthly"]] == ["1000.00", "1200.00"]
    assert [item["net_cash_after_emi_inr"] for item in result["monthly"]] == ["600.00", "700.00"]


def test_negative_result_reports_cash_gap():
    result = calculate_stress_test(
        base_monthly=BASE,
        revenue_shock_pct=Decimal("-100"),
        expense_shock_pct=Decimal("0"),
        payment_delay_days=0,
        duration_months=1,
        selected_loan_emi=Decimal("200"),
    )
    assert result["monthly"][0]["net_cash_after_emi_inr"] == "-600.00"
    assert result["monthly"][0]["cash_gap_inr"] == "600.00"
    assert any("cash gap" in warning for warning in result["warnings"])


def test_payment_delay_shifts_cash_without_deleting_it():
    result = calculate_stress_test(
        base_monthly=BASE,
        revenue_shock_pct=Decimal("0"),
        expense_shock_pct=Decimal("0"),
        payment_delay_days=31,
        duration_months=3,
        selected_loan_emi=Decimal("0"),
    )
    assert [item["projected_inflows_inr"] for item in result["monthly"]] == ["0.00", "0.00", "1000.00"]
    assert result["metrics"]["receipts_delayed_beyond_horizon_inr"] == "2200.00"
    assert Decimal(result["metrics"]["total_projected_inflows_inr"]) + Decimal(result["metrics"]["receipts_delayed_beyond_horizon_inr"]) == Decimal("3200.00")
    assert "shift receipt timing" in result["metrics"]["cash_conservation_note"]


def test_combined_crisis_applies_each_shock_and_seasonality():
    result = calculate_stress_test(
        base_monthly=BASE,
        revenue_shock_pct=Decimal("-20"),
        expense_shock_pct=Decimal("15"),
        payment_delay_days=45,
        duration_months=3,
        selected_loan_emi=Decimal("100"),
        seasonal_weaker_months=2,
    )
    assert result["scenario"]["payment_delay_months"] == 2
    assert result["monthly"][0]["projected_inflows_inr"] == "0.00"
    assert result["monthly"][2]["projected_inflows_inr"] == "640.00"
    assert result["monthly"][2]["net_cash_after_emi_inr"] == "80.00"
