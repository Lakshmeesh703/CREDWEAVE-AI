from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.auth import business_access
from app.db.session import SessionLocal
from app.models import Business, Counterparty, DataSource, Invoice, PaymentLink, Transaction
from app.services.trust_graph import build_trust_graph

router = APIRouter(prefix="/api")


def _graph(business_id: str) -> dict:
    with SessionLocal() as db:
        business = db.scalar(select(Business).where(Business.id == business_id))
        if business is None:
            raise HTTPException(status_code=404, detail="Business not found.")
        sources = db.scalars(select(DataSource).where(DataSource.business_id == business_id)).all()
        counterparties = db.scalars(select(Counterparty).where(Counterparty.business_id == business_id)).all()
        invoices = db.scalars(select(Invoice).where(Invoice.business_id == business_id)).all()
        transactions = db.scalars(select(Transaction).where(Transaction.business_id == business_id)).all()
        links = db.scalars(select(PaymentLink).where(PaymentLink.business_id == business_id)).all()
        return build_trust_graph(
            business=business,
            sources=sources,
            counterparties=counterparties,
            invoices=invoices,
            transactions=transactions,
            payment_links=links,
        )


@router.get("/businesses/{business_id}/trust-graph", dependencies=[Depends(business_access)])
def trust_graph(business_id: str) -> dict:
    result = _graph(business_id)
    result["business_id"] = business_id
    return result


@router.get("/businesses/{business_id}/graph-findings", dependencies=[Depends(business_access)])
def graph_findings(business_id: str) -> dict:
    result = _graph(business_id)
    return {
        "business_id": business_id,
        "rule_version": result["rule_version"],
        "provenance": result["provenance"],
        "anomalies": result["anomalies"],
    }
