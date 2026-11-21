import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from app.credit_passport import build_passport
from app.auth import Principal, business_access, businesses_for, current_user, owned_business
from app.db.session import SessionLocal
from app.models import Assessment, Business, Review
from app.models.entities import PortalAccount, ReviewStatus
from app.schemas.contracts import BusinessResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

CHECKLIST_KEYS = (
    "identity_reviewed",
    "evidence_findings_reviewed",
    "scenario_comparison_reviewed",
    "limitations_acknowledged",
    "human_decision_pending",
)


class ReviewCreate(BaseModel):
    reviewer_name_or_alias: str | None = Field(default=None, min_length=1, max_length=120)
    assessment_id: str | None = Field(default=None, max_length=36)
    status: ReviewStatus = ReviewStatus.PENDING
    reason: str = Field(min_length=1, max_length=4000)
    checklist: dict[str, bool] = Field(default_factory=dict)


def _business(db, business_id: str) -> Business:
    business = db.get(Business, business_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Business not found.")
    return business


def _assessment_order():
    return desc(Assessment.created_at), desc(Assessment.id)


def _latest_assessment(db, business_id: str) -> Assessment:
    assessment = db.scalar(
        select(Assessment)
        .where(Assessment.business_id == business_id)
        .order_by(*_assessment_order())
    )
    if assessment is None:
        raise HTTPException(status_code=404, detail="Create an assessment before starting lender review.")
    return assessment


@router.get("/lender/queue")
def lender_queue(user: Principal = Depends(current_user)) -> list[dict[str, Any]]:
    if user.demo or user.role != "lender":
        raise HTTPException(403, "Lender access is required.")
    latest_assessment = (
        select(Assessment.id).where(Assessment.business_id == Business.id)
        .order_by(*_assessment_order()).limit(1).correlate(Business).scalar_subquery()
    )
    latest_status = (
        select(Review.status).where(Review.assessment_id == latest_assessment, Review.reviewer_account_id == user.id)
        .order_by(desc(Review.updated_at), desc(Review.id)).limit(1).correlate(Business).scalar_subquery()
    )
    query = businesses_for(user).add_columns(latest_assessment, latest_status).order_by(desc(Business.created_at))
    with SessionLocal() as db:
        return [
            {"business": BusinessResponse.model_validate(business).model_dump(mode="json"),
             "assessment_id": assessment_id,
             "review_status": status or ("awaiting_review" if assessment_id else "no_passport")}
            for business, assessment_id, status in db.execute(query)
        ]


@router.get("/businesses/{business_id}/review-workspace")
def review_workspace(business_id: str, user: Principal = Depends(business_access)) -> dict[str, Any]:
    with SessionLocal() as db:
        business = _business(db, business_id)
        assessment = _latest_assessment(db, business_id)
        query = select(Review).where(Review.assessment_id == assessment.id).order_by(desc(Review.updated_at))
        if user.role == "lender":
            query = query.where(Review.reviewer_account_id == user.id)
        reviews = list(db.scalars(query))
        passport = build_passport(business, assessment)
        return {
            "business": {
                "id": business.id,
                "name": business.name,
                "consent_status": getattr(business.consent_status, "value", business.consent_status),
            },
            "passport": passport,
            "evidence_findings": passport["snapshot"]["evidence_dna"]["findings"],
            "scenario_comparison": passport["snapshot"]["cashflow_twin"],
            "consent": passport["consent"],
            "reviews": [
                {
                    "id": review.id,
                    "assessment_id": review.assessment_id,
                    "reviewer_name_or_alias": review.reviewer_name_or_alias,
                    "status": getattr(review.status, "value", review.status),
                    "reason": review.reason,
                    "checklist": review.checklist_json or {},
                    "rule_version": review.rule_version,
                    "updated_at": review.updated_at.isoformat(),
                }
                for review in reviews
            ],
            "checklist_keys": CHECKLIST_KEYS,
            "limitations": [
                *(["Synthetic demo reviewer workspace; production requires authentication."] if user.demo else []),
                "Review status is not a loan approval or denial.",
            ],
        }


@router.post("/businesses/{business_id}/reviews", status_code=201)
def create_review(business_id: str, payload: ReviewCreate, user: Principal = Depends(business_access)) -> dict[str, Any]:
    if not user.demo and user.role != "lender":
        raise HTTPException(403, "Lender access is required to record a review.")
    if not payload.reason.strip():
        raise HTTPException(422, "Enter a reason for this review.")
    with SessionLocal.begin() as db:
        if not user.demo:
            role = db.scalar(select(PortalAccount.role).where(PortalAccount.id == user.id).with_for_update())
            if role != "lender":
                raise HTTPException(403, "Lender access is required to record a review.")
        db.scalar(select(Business.id).where(Business.id == business_id).with_for_update())
        if db.scalar(businesses_for(user).where(Business.id == business_id)) is None:
            raise HTTPException(404, "Business not found.")
        assessment = _latest_assessment(db, business_id)
        if not user.demo and payload.assessment_id != assessment.id:
            raise HTTPException(409, "Reload the current Passport before recording a review.")
        checklist = {key: bool(payload.checklist.get(key, False)) for key in CHECKLIST_KEYS}
        review = Review(
            assessment_id=assessment.id,
            reviewer_name_or_alias=(payload.reviewer_name_or_alias or "Demo reviewer") if user.demo else f"Lender {user.id[:8]}",
            reviewer_account_id=None if user.demo else user.id,
            status=payload.status,
            reason=payload.reason,
            checklist_json=checklist,
            rule_version=assessment.rule_version,
            updated_at=datetime.utcnow(),
        )
        db.add(review)
        db.flush()
        logger.info(
            "manual_review_recorded business_id=%s assessment_id=%s review_id=%s status=%s rule_version=%s",
            business_id, assessment.id, review.id, payload.status.value, assessment.rule_version,
        )
        return {
            "id": review.id,
            "assessment_id": review.assessment_id,
            "reviewer_name_or_alias": review.reviewer_name_or_alias,
            "status": review.status.value,
            "reason": review.reason,
            "checklist": checklist,
            "rule_version": review.rule_version,
            "updated_at": review.updated_at.isoformat(),
        }


@router.post("/businesses/{business_id}/consent")
def update_consent(
    business_id: str,
    source_upload_consent: bool,
    passport_sharing_consent: bool,
    user: Principal = Depends(owned_business),
) -> dict[str, bool]:
    if not user.demo:
        raise HTTPException(403, "Manage upload consent in the profile and sharing through lender access grants.")
    with SessionLocal.begin() as db:
        _business(db, business_id)
        business = db.get(Business, business_id)
        business.source_upload_consent = source_upload_consent
        business.passport_sharing_consent = passport_sharing_consent
        return {"source_upload": source_upload_consent, "passport_sharing": passport_sharing_consent}
