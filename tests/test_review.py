import io
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine
from app.main import app
from app.models import Business
from app.models.entities import ConsentStatus

client = TestClient(app)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_consent_controls_block_upload_and_passport_export() -> None:
    with SessionLocal.begin() as db:
        business = Business(
            name="Synthetic Consent Shop",
            sector="Retail",
            operating_months=6,
            city="Pune",
            consent_status=ConsentStatus.PENDING,
            source_upload_consent=False,
            passport_sharing_consent=False,
        )
        db.add(business)
        db.flush()
        business_id = business.id

    csv = b"external_ref,transaction_date,amount_inr,direction,payment_channel,description,currency\nTX-1,2026-01-01,10.00,credit,upi,Receipt,INR\n"
    response = client.post(
        f"/api/businesses/{business_id}/imports/transactions",
        files={"file": ("transactions.csv", io.BytesIO(csv), "text/csv")},
    )
    assert response.status_code == 403

    client.post(
        f"/api/businesses/{business_id}/consent",
        params={"source_upload_consent": "true", "passport_sharing_consent": "true"},
    )
    assessment = client.post(f"/api/businesses/{business_id}/assess")
    assert assessment.status_code == 201
    passport = client.get(f"/api/businesses/{business_id}/credit-passport")
    assert passport.status_code == 200
    assert passport.json()["export"]["allowed"] is True


def test_review_records_manual_status_checklist_and_rule_version() -> None:
    with SessionLocal.begin() as db:
        business = Business(
            name="Synthetic Review Shop",
            sector="Services",
            operating_months=6,
            city="Pune",
            consent_status=ConsentStatus.GRANTED,
        )
        db.add(business)
        db.flush()
        business_id = business.id

    assessment = client.post(f"/api/businesses/{business_id}/assess").json()
    review = client.post(
        f"/api/businesses/{business_id}/reviews",
        json={
            "reviewer_name_or_alias": "demo-lender",
            "status": "needs_more_information",
            "reason": "Request the missing supplier statement.",
            "checklist": {"identity_reviewed": True, "limitations_acknowledged": True},
        },
    )
    assert review.status_code == 201
    assert review.json()["status"] == "needs_more_information"
    assert review.json()["rule_version"] == assessment["rule_version"]
    assert review.json()["checklist"]["identity_reviewed"] is True
    assert review.json()["checklist"]["human_decision_pending"] is False

    workspace = client.get(f"/api/businesses/{business_id}/review-workspace")
    assert workspace.status_code == 200
    assert workspace.json()["reviews"][0]["reason"] == "Request the missing supplier statement."
    assert "production requires authentication" in " ".join(workspace.json()["limitations"])
