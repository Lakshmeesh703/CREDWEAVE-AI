import io
import os
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine
from app.main import app


client = TestClient(app)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _business() -> str:
    response = client.post(
        "/api/businesses",
        json={
            "name": "Synthetic Intake Shop",
            "sector": "Retail",
            "operating_months": 18,
            "city": "Pune",
            "consent_status": "granted",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_business_creation_and_summary() -> None:
    business_id = _business()
    response = client.get(f"/api/businesses/{business_id}/records-summary")
    assert response.status_code == 200
    assert response.json()["counts"] == {
        "transactions": 0,
        "invoices": 0,
        "obligations": 0,
        "counterparties": 0,
        "sources": 0,
    }


def test_invalid_transaction_csv_is_rejected_without_partial_write() -> None:
    business_id = _business()
    csv = b"external_ref,transaction_date,amount_inr,direction,payment_channel,description,currency\nTX-1,2026-01-01,10.123,credit,upi,Receipt,INR\n"
    response = client.post(
        f"/api/businesses/{business_id}/imports/transactions",
        files={"file": ("transactions.csv", io.BytesIO(csv), "text/csv")},
    )
    assert response.status_code == 422
    summary = client.get(f"/api/businesses/{business_id}/records-summary").json()
    assert summary["counts"]["transactions"] == 0
    assert summary["counts"]["sources"] == 0


def test_valid_transaction_import_and_duplicate_hash_protection() -> None:
    business_id = _business()
    csv = b"external_ref,transaction_date,amount_inr,direction,payment_channel,description,currency\nTX-1,2026-01-01,10.00,credit,upi,Receipt,INR\n"
    first = client.post(
        f"/api/businesses/{business_id}/imports/transactions",
        files={"file": ("transactions.csv", io.BytesIO(csv), "text/csv")},
    )
    duplicate = client.post(
        f"/api/businesses/{business_id}/imports/transactions",
        files={"file": ("transactions-copy.csv", io.BytesIO(csv), "text/csv")},
    )
    assert first.status_code == 200
    assert first.json()["accepted_rows"] == 1
    assert duplicate.status_code == 409
    assert client.get(f"/api/businesses/{business_id}/records-summary").json()["counts"]["transactions"] == 1


def test_missing_transaction_column_is_rejected() -> None:
    business_id = _business()
    csv = b"external_ref,transaction_date,amount_inr,direction,payment_channel,currency\nTX-1,2026-01-01,10.00,credit,upi,INR\n"
    response = client.post(
        f"/api/businesses/{business_id}/imports/transactions",
        files={"file": ("missing-description.csv", io.BytesIO(csv), "text/csv")},
    )
    assert response.status_code == 422
    assert "missing columns: description" in response.json()["detail"]


def test_invalid_transaction_date_is_rejected() -> None:
    business_id = _business()
    csv = b"external_ref,transaction_date,amount_inr,direction,payment_channel,description,currency\nTX-1,01-01-2026,10.00,credit,upi,Receipt,INR\n"
    response = client.post(
        f"/api/businesses/{business_id}/imports/transactions",
        files={"file": ("invalid-date.csv", io.BytesIO(csv), "text/csv")},
    )
    assert response.status_code == 422
    assert "ISO date" in response.json()["detail"]


def test_cross_business_id_is_not_accessible() -> None:
    response = client.get(f"/api/businesses/{uuid4()}")
    assert response.status_code == 404
