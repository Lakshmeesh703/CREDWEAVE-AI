from __future__ import annotations

from decimal import Decimal
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import business_access
from app.db.session import SessionLocal
from app.models import Business, DataSource, Invoice, Transaction
from app.models.entities import InvoiceDirection, TransactionDirection
from app.services.evidence_dna import EvidenceRecord, calculate_evidence_dna
from app.services.gateway import gateway_available, status_counts

router = APIRouter(prefix="/api")


def _enum_value(value):
    return getattr(value, "value", value)


def _record_data(
    db: Session, business_id: str,
) -> tuple[Business, list[EvidenceRecord], list[EvidenceRecord], bool]:
    business = db.scalar(select(Business).where(Business.id == business_id))
    if business is None:
        raise HTTPException(status_code=404, detail="Business not found.")
    sources = {
        source.id: source
        for source in db.scalars(select(DataSource).where(DataSource.business_id == business_id)).all()
    }
    transactions = db.scalars(select(Transaction).where(Transaction.business_id == business_id)).all()
    invoices = db.scalars(select(Invoice).where(Invoice.business_id == business_id)).all()

    transaction_records = [
        EvidenceRecord(
            record_id=item.id,
            source_id=item.source_id,
            kind="transaction",
            period=item.transaction_date.strftime("%Y-%m"),
            amount=Decimal(item.amount_inr),
            record_date=item.transaction_date,
            counterparty_id=item.counterparty_id,
            direction=_enum_value(item.direction),
        )
        for item in transactions
        if item.currency == "INR" and item.source_id in sources
    ]
    invoice_records = [
        EvidenceRecord(
            record_id=item.id,
            source_id=item.source_id,
            kind="invoice",
            period=item.issued_at.strftime("%Y-%m"),
            amount=Decimal(item.total_inr),
            record_date=item.issued_at,
            counterparty_id=item.counterparty_id,
            direction=_enum_value(item.direction),
        )
        for item in invoices
        if _enum_value(item.direction) == "receivable" and item.source_id in sources
    ]
    return business, transaction_records, invoice_records, bool(sources) and all(
        source.synthetic for source in sources.values()
    )


def _calculate(business_id: str, db: Session | None = None) -> dict:
    if db is None:
        with SessionLocal() as session:
            return _calculate(business_id, session)
    business, transactions, invoices, synthetic = _record_data(db, business_id)
    observed_periods = sorted({item.period for item in (*transactions, *invoices)})
    periods: list[str] = []
    if observed_periods:
        start = date.fromisoformat(f"{observed_periods[0]}-01")
        end = date.fromisoformat(f"{observed_periods[-1]}-01")
        current = start
        while current <= end:
            periods.append(current.strftime("%Y-%m"))
            if current == end:
                break
            current = date(
                current.year + (current.month == 12),
                1 if current.month == 12 else current.month + 1,
                1,
            )
    claim = Decimal("100000") if synthetic and business.name.startswith(("Business A -", "Business B -")) else None
    result = calculate_evidence_dna(
        transactions,
        invoices,
        expected_periods=periods,
        reported_monthly_revenue_inr=claim,
    )
    if gateway_available(db):
        result["gateway_status_counts"] = status_counts(db, business_id)
    result["business_id"] = business.id
    result["business_name"] = business.name
    result["provenance"] = {
        "data_scope": "business-scoped records only",
        "synthetic": synthetic,
        "source_ids": sorted({item.source_id for item in (*transactions, *invoices)}),
        "rule_version": result["rule_version"],
    }
    return result


@router.get("/businesses/{business_id}/evidence-dna", dependencies=[Depends(business_access)])
def evidence_dna(business_id: str) -> dict:
    return _calculate(business_id)


@router.get("/businesses/{business_id}/evidence-findings", dependencies=[Depends(business_access)])
def evidence_findings(business_id: str) -> dict:
    result = _calculate(business_id)
    return {
        "business_id": result["business_id"],
        "rule_version": result["rule_version"],
        "provenance": result["provenance"],
        "findings": result["findings"],
    }
