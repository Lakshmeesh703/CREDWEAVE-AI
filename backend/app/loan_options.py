from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import Principal, business_access
from app.financial import financial_summary
from app.services.loan_structuring import build_loan_options
from app.services.stress_testing import PRESETS, calculate_stress_test
from app.stress_tests import _base_from_summary

router = APIRouter(prefix="/api")


class ScenarioMonth(BaseModel):
    month: str = "scenario"
    inflows_inr: Decimal = Field(ge=0)
    outflows_inr: Decimal = Field(ge=0)


class LoanOptionsRequest(BaseModel):
    principal_inr: Decimal = Field(gt=0, le=Decimal("999999999999.99"))
    annual_interest_rate_pct: Decimal = Field(ge=0, le=100)
    tenure_months: list[int] = Field(min_length=1, max_length=12)
    origination_fee_inr: Decimal = Field(default=Decimal("0"), ge=0, le=Decimal("999999999999.99"))
    selected_scenario: list[ScenarioMonth] | None = Field(default=None, min_length=1, max_length=24)
    scenario_preset: Literal["normal", "combined_crisis"] | None = None


@router.post("/businesses/{business_id}/loan-options")
def loan_options(business_id: str, request: LoanOptionsRequest, user: Principal = Depends(business_access)) -> dict[str, Any]:
    summary = financial_summary(business_id)
    scenario = _base_from_summary(summary)
    scope = "business-scoped observed monthly financial summary"
    if request.selected_scenario is not None:
        if not user.demo or request.scenario_preset is not None:
            raise HTTPException(422, "Choose a scenario preset based on the uploaded transactions.")
        scenario = [item.model_dump() for item in request.selected_scenario]
        scope = "caller-supplied CashFlow Twin scenario"
    if not scenario:
        raise HTTPException(422, "Upload operating transactions before comparing loan options.")
    if request.scenario_preset is not None:
        preset = PRESETS[request.scenario_preset]
        result = calculate_stress_test(
            base_monthly=scenario,
            duration_months=6,
            selected_loan_emi=Decimal("0"),
            revenue_shock_pct=Decimal(preset["revenue_shock_pct"]),
            expense_shock_pct=Decimal(preset["expense_shock_pct"]),
            payment_delay_days=preset["payment_delay_days"],
            seasonal_weaker_months=preset["seasonal_weaker_months"],
        )
        scenario = [
            {"month": row["label"], "inflows_inr": row["projected_inflows_inr"], "outflows_inr": row["projected_outflows_inr"]}
            for row in result["monthly"]
        ]
        scope = f'{preset["label"]} using uploaded business transactions'
    try:
        result = build_loan_options(
            principal=request.principal_inr,
            annual_rate_pct=request.annual_interest_rate_pct,
            tenure_months=request.tenure_months,
            origination_fee=request.origination_fee_inr,
            scenario_monthly=scenario,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result["business_id"] = business_id
    result["provenance"] = {
        "synthetic": summary["provenance"]["synthetic"],
        "source_ids": summary["provenance"]["source_ids"],
        "scenario_scope": scope,
    }
    return result
