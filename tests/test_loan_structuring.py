from decimal import Decimal

from app.services.loan_structuring import build_loan_options, calculate_emi


SCENARIO = [
    {"month": "2024-01", "inflows_inr": "100000", "outflows_inr": "70000"},
    {"month": "2024-02", "inflows_inr": "80000", "outflows_inr": "70000"},
]


def test_emi_matches_independent_standard_example():
    emi = calculate_emi(Decimal("100000"), Decimal("12"), 12)
    assert emi.quantize(Decimal("0.01")) == Decimal("8884.88")


def test_zero_interest_and_fee_are_disclosed():
    result = build_loan_options(
        principal=Decimal("120000"),
        annual_rate_pct=Decimal("0"),
        tenure_months=[6],
        origination_fee=Decimal("1200"),
        scenario_monthly=SCENARIO,
    )
    option = result["options"][0]
    assert option["emi_inr"] == "20000.00"
    assert option["interest_cost_inr"] == "0.00"
    assert option["total_cost_inr"] == "121200.00"


def test_requested_tenures_and_rounding_are_complete():
    result = build_loan_options(
        principal=Decimal("200000"),
        annual_rate_pct=Decimal("18"),
        tenure_months=[6, 12, 18, 24],
        origination_fee=Decimal("0"),
        scenario_monthly=SCENARIO,
    )

    assert [option["tenure_months"] for option in result["options"]] == [6, 12, 18, 24]
    assert all(Decimal(option["emi_inr"]).as_tuple().exponent == -2 for option in result["options"])


def test_shortfall_requires_review_and_months_are_explained():
    result = build_loan_options(
        principal=Decimal("200000"),
        annual_rate_pct=Decimal("12"),
        tenure_months=[6, 12],
        origination_fee=Decimal("0"),
        scenario_monthly=SCENARIO,
    )
    assert len(result["options"]) == 2
    assert result["options"][0]["affordability_status"] == "requires review"
    assert result["options"][0]["monthly"][1]["net_cash_after_proposed_emi_inr"].startswith("-")
    assert result["options"][1]["minimum_dscr"] is not None
