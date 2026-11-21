from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.auth import Principal, business_access
from app.db.session import SessionLocal
from app.financial import financial_summary
from app.models import Business
from app.services.stress_testing import PRESETS, calculate_stress_test

router = APIRouter(prefix="/api")


class BaseMonth(BaseModel):
    month: str = "base"
    inflows_inr: Decimal = Field(ge=0)
    outflows_inr: Decimal = Field(ge=0)


class StressTestRequest(BaseModel):
    base_monthly: list[BaseMonth] | None = Field(default=None, min_length=1, max_length=120)
    revenue_shock_pct: Decimal = Field(default=Decimal("0"), ge=-100, le=100)
    expense_shock_pct: Decimal = Field(default=Decimal("0"), ge=-100, le=500)
    payment_delay_days: int = Field(default=0, ge=0, le=365)
    duration_months: int = Field(default=6, ge=1, le=24)
    selected_loan_emi: Decimal = Field(default=Decimal("0"), ge=0, le=Decimal("999999999999.99"))
    seasonal_weaker_months: int = Field(default=0, ge=0, le=24)


def _base_from_summary(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"month": item["month"], "inflows_inr": item["inflows_inr"], "outflows_inr": item["outflows_inr"]}
        for item in summary["monthly"]
    ]


@router.get("/businesses/{business_id}/stress-tests/presets", dependencies=[Depends(business_access)])
def stress_test_presets(business_id: str) -> dict[str, Any]:
    with SessionLocal() as db:
        if db.scalar(select(Business).where(Business.id == business_id)) is None:
            raise HTTPException(status_code=404, detail="Business not found.")
    return {"business_id": business_id, "presets": PRESETS}


@router.post("/businesses/{business_id}/stress-tests")
def stress_test(business_id: str, request: StressTestRequest, user: Principal = Depends(business_access)) -> dict[str, Any]:
    with SessionLocal() as db:
        if db.scalar(select(Business).where(Business.id == business_id)) is None:
            raise HTTPException(status_code=404, detail="Business not found.")
    summary = financial_summary(business_id)
    if request.base_monthly is not None and not user.demo:
        raise HTTPException(422, "CashFlow Twin uses the uploaded transactions for this business.")
    base = [item.model_dump() for item in request.base_monthly] if request.base_monthly else _base_from_summary(summary)
    if not base:
        raise HTTPException(status_code=422, detail="Upload operating transactions before running CashFlow Twin.")
    try:
        result = calculate_stress_test(
            base_monthly=base,
            revenue_shock_pct=request.revenue_shock_pct,
            expense_shock_pct=request.expense_shock_pct,
            payment_delay_days=request.payment_delay_days,
            duration_months=request.duration_months,
            selected_loan_emi=request.selected_loan_emi,
            seasonal_weaker_months=request.seasonal_weaker_months,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result["business_id"] = business_id
    result["provenance"] = {
        "synthetic": summary["provenance"]["synthetic"],
        "source_ids": summary["provenance"]["source_ids"],
        "base_data_scope": "business-scoped observed monthly financial summary" if request.base_monthly is None else "caller-supplied monthly model",
    }
    return result
