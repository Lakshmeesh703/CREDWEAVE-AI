from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.auth import business_access
from app.db.session import SessionLocal
from app.models import Business, Obligation, Transaction
from app.services.financial_health import calculate_financial_health, supplier_concentration_percent
from app.models import Counterparty, DataSource

router = APIRouter(prefix="/api")


@router.get("/businesses/{business_id}/financial-summary", dependencies=[Depends(business_access)])
def financial_summary(business_id: str) -> dict:
    with SessionLocal() as db:
        business = db.scalar(select(Business).where(Business.id == business_id))
        if business is None:
            raise HTTPException(status_code=404, detail="Business not found.")
        transactions = db.scalars(select(Transaction).where(Transaction.business_id == business_id)).all()
        obligations = db.scalars(select(Obligation).where(Obligation.business_id == business_id)).all()
        counterparties = db.scalars(select(Counterparty).where(Counterparty.business_id == business_id)).all()
        source_list = db.scalars(select(DataSource).where(DataSource.business_id == business_id)).all()
        result = calculate_financial_health(
            transactions=transactions,
            obligations=obligations,
            supplier_concentration_percent=supplier_concentration_percent(transactions, counterparties),
        )
        result.update(
            {
                "business_id": business_id,
                "business_name": business.name,
                "provenance": {
                    "synthetic": bool(source_list) and all(source.synthetic for source in source_list),
                    "source_ids": sorted({source.id for source in source_list}),
                    "data_scope": "business-scoped normalized transactions and obligations",
                    "rule_version": result["rule_version"],
                },
            }
        )
        return result
