from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select

from app.auth import Principal, business_access
from app.db.session import SessionLocal
from app.models import Assessment, Business, Review
from app.intake import has_source_upload_consent

router = APIRouter(prefix="/api")


@router.get("/businesses/{business_id}/credit-passport")
def credit_passport(business_id: str, user: Principal = Depends(business_access)) -> dict:
    with SessionLocal() as db:
        business = db.scalar(select(Business).where(Business.id == business_id))
        if business is None:
            raise HTTPException(status_code=404, detail="Business not found.")
        assessment = db.scalar(
            select(Assessment)
            .where(Assessment.business_id == business_id)
            .order_by(desc(Assessment.created_at), desc(Assessment.id))
        )
        if assessment is None:
            raise HTTPException(status_code=404, detail="Create an assessment before generating a credit passport.")
        review_query = select(Review.status, Review.updated_at).where(Review.assessment_id == assessment.id)
        if user.role == "lender":
            review_query = review_query.where(Review.reviewer_account_id == user.id)
        review = db.execute(review_query.order_by(desc(Review.updated_at), desc(Review.id)).limit(1)).first()
        report = build_passport(business, assessment)
        report["latest_review"] = {"status": review.status, "updated_at": review.updated_at.isoformat()} if review else None
        return report


def build_passport(business: Business, assessment: Assessment) -> dict:
    snapshot = assessment.snapshot_json
    sharing_allowed = (
        business.passport_sharing_consent
        if business.passport_sharing_consent is not None
        else getattr(business.consent_status, "value", business.consent_status) == "granted"
    )
    return {
        "passport_version": "credit-passport.v1",
        "assessment_id": assessment.id,
        "business_id": business.id,
        "created_at": assessment.created_at.isoformat(),
        "rule_version": assessment.rule_version,
        "status": "Prepared for Human Lender Review",
        "snapshot": snapshot,
        "disclosures": [
            "This passport is decision support for a human lender, never an automatic approval or denial.",
            "Synthetic or simulated records are not external verification.",
            "Missing evidence is unknown evidence, not proof of fraud or repayment risk.",
            "Loan options are illustrative affordability scenarios, not eligibility or guarantees.",
        ],
        "consent": {
            "source_upload": has_source_upload_consent(business),
            "passport_sharing": sharing_allowed,
        },
        "export": {
            "format": "browser-print-to-pdf",
            "filename": f"credweave-credit-passport-{assessment.id}.pdf",
            "allowed": sharing_allowed,
            "blocked_reason": None if sharing_allowed else "Passport sharing consent is required before export.",
        },
    }
