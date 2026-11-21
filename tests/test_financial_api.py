from datetime import date
from decimal import Decimal

from app.db.session import SessionLocal
from app.models import Business, DataSource, Obligation, Transaction
from app.models.entities import ConsentStatus, ParsingStatus, PaymentChannel, SourceKind, TransactionDirection
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def setup_function() -> None:
    from app.db.session import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_financial_summary_endpoint_is_business_scoped_and_explicit() -> None:
    with SessionLocal.begin() as db:
        business = Business(name="SYNTHETIC Health Shop", sector="Retail", operating_months=12, city="Pune", consent_status=ConsentStatus.GRANTED)
        db.add(business)
        db.flush()
        source = DataSource(business_id=business.id, kind=SourceKind.BANK, synthetic=True, source_label="SYNTHETIC bank", file_hash="hash-api", parsing_status=ParsingStatus.IMPORTED)
        db.add(source)
        db.flush()
        db.add_all([
            Transaction(business_id=business.id, source_id=source.id, external_ref="credit-1", transaction_date=date(2025, 7, 1), amount_inr=Decimal("1000.00"), direction=TransactionDirection.CREDIT, payment_channel=PaymentChannel.UPI, description="customer receipt", currency="INR"),
            Transaction(business_id=business.id, source_id=source.id, external_ref="debit-1", transaction_date=date(2025, 7, 2), amount_inr=Decimal("300.00"), direction=TransactionDirection.DEBIT, payment_channel=PaymentChannel.UPI, description="supplier payment", currency="INR"),
        ])
        db.add(Obligation(business_id=business.id, monthly_payment_inr=Decimal("100.00"), description="SYNTHETIC loan"))
        business_id = business.id

    response = client.get(f"/api/businesses/{business_id}/financial-summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["business_id"] == business_id
    assert payload["metrics"]["net_operating_cash_flow"]["value"] == "700.00"
    assert payload["metrics"]["monthly_debt_obligations"]["value"] == "100.00"
    assert payload["metrics"]["net_operating_cash_flow"]["unit"] == "INR"
    assert payload["provenance"]["synthetic"] is True
