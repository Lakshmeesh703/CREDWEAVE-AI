from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select

from app.auth import Principal, business_access, owned_business
from app.db.session import SessionLocal
from app.evidence import _calculate as calculate_evidence
from app.financial import financial_summary
from app.models import Assessment, Business, DataSource
from app.models.entities import AssessmentStatus
from app.services.risk_rules import evaluate_rules
from app.services.stress_testing import calculate_stress_test
from app.services.loan_structuring import build_loan_options
from app.trust_graph import _graph

router = APIRouter(prefix="/api")


@router.post("/businesses/{business_id}/assess", status_code=201)
def assess_business(business_id: str, user: Principal = Depends(owned_business)) -> dict:
    return create_assessment(business_id, require_cash_flow=not user.demo)


def create_assessment(business_id: str, *, require_cash_flow: bool = False) -> dict:
    financial = financial_summary(business_id)
    if require_cash_flow and not financial["monthly"]:
        raise HTTPException(422, "Upload operating transactions before creating an assessment and Credit Passport.")
    evidence = calculate_evidence(business_id)
    snapshot = evaluate_rules(financial, evidence)
    with SessionLocal() as db:
        business = db.scalar(select(Business).where(Business.id == business_id))
        if business is None:
            raise HTTPException(status_code=404, detail="Business not found.")
        sources = db.scalars(select(DataSource).where(DataSource.business_id == business_id)).all()
        source_inventory = [
            {
                "source_id": source.id,
                "kind": getattr(source.kind, "value", source.kind),
                "source_label": source.source_label,
                "synthetic": source.synthetic,
                "imported_at": source.imported_at.isoformat(),
                "parsing_status": getattr(source.parsing_status, "value", source.parsing_status),
            }
            for source in sources
        ]
        identity = {
            "id": business.id,
            "name": business.name,
            "sector": business.sector,
            "operating_months": business.operating_months,
            "city": business.city,
            "consent_status": getattr(business.consent_status, "value", business.consent_status),
        }
    base_monthly = [
        {"month": item["month"], "inflows_inr": item["inflows_inr"], "outflows_inr": item["outflows_inr"]}
        for item in financial["monthly"]
    ]
    if base_monthly:
        normal_twin = calculate_stress_test(
            base_monthly=base_monthly,
            revenue_shock_pct=0, expense_shock_pct=0, payment_delay_days=0,
            duration_months=max(1, min(6, len(base_monthly))), selected_loan_emi=0,
        )
        crisis_twin = calculate_stress_test(
            base_monthly=base_monthly,
            revenue_shock_pct=-20, expense_shock_pct=15, payment_delay_days=45,
            duration_months=max(1, min(6, len(base_monthly))), selected_loan_emi=0,
            seasonal_weaker_months=2,
        )
        loan_options = build_loan_options(
            principal=200000, annual_rate_pct=18, tenure_months=[6, 12, 18, 24],
            origination_fee=0, scenario_monthly=base_monthly,
        )
    else:
        empty_twin = {
            "rule_version": "cashflow-twin.v1", "monthly": [],
            "metrics": {"minimum_net_cash_after_emi_inr": "0.00"},
            "warnings": ["No observed monthly cash-flow data is available."],
            "assumptions": [],
        }
        normal_twin = empty_twin
        crisis_twin = empty_twin
        loan_options = {"options": [], "assumptions": ["No monthly scenario was available."]}
    snapshot.update({
        "financial_summary": financial,
        "evidence_dna": evidence,
        "trust_graph": _graph(business_id),
        "business": identity,
        "source_inventory": source_inventory,
        "cashflow_twin": {"normal": normal_twin, "combined_crisis": crisis_twin},
        "loan_options": loan_options,
        "business_id": business_id,
    })
    with SessionLocal.begin() as db:
        if db.scalar(select(Business.id).where(Business.id == business_id).with_for_update()) is None:
            raise HTTPException(status_code=404, detail="Business not found.")
        assessment = Assessment(
            business_id=business_id,
            rule_version=snapshot["rule_version"],
            status=AssessmentStatus.READY,
            snapshot_json=snapshot,
            limitations_json=snapshot["financial_summary"]["limitations"],
        )
        db.add(assessment)
        db.flush()
        return {"assessment_id": assessment.id, "business_id": business_id, "created_at": assessment.created_at.isoformat(), "rule_version": assessment.rule_version, "status": getattr(assessment.status, "value", assessment.status), "snapshot": snapshot}


@router.get("/businesses/{business_id}/assessments/latest", dependencies=[Depends(business_access)])
def latest_assessment(business_id: str) -> dict:
    with SessionLocal() as db:
        assessment = db.scalar(
            select(Assessment)
            .where(Assessment.business_id == business_id)
            .order_by(desc(Assessment.created_at))
        )
        if assessment is None:
            raise HTTPException(status_code=404, detail="No assessment exists for this business.")
        return {
            "assessment_id": assessment.id,
            "business_id": assessment.business_id,
            "created_at": assessment.created_at.isoformat(),
            "rule_version": assessment.rule_version,
            "status": getattr(assessment.status, "value", assessment.status),
            "snapshot": assessment.snapshot_json,
            "limitations": assessment.limitations_json,
        }
