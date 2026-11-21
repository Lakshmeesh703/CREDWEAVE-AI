"""Business-scoped APIs for provenance, verification history and reconciliation."""

from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.auth import business_access, owned_business
from app.db.session import SessionLocal
from app.evidence import _calculate
from app.models.entities import Business, DataSource, Invoice, Obligation, Transaction
from app.models.gateway import RecordProvenance, VerificationEvent, VerificationStatus
from app.services.gateway import gateway_available, latest_results, reconcile, record_id_of, status_counts

router = APIRouter(prefix="/api/businesses/{business_id}/verified-evidence")


def _ready(db: Session) -> None:
    if not gateway_available(db):
        raise HTTPException(503, "The evidence gateway is temporarily unavailable.")


def _event(event: VerificationEvent) -> dict:
    return {
        "event_id": event.id,
        "status": event.status,
        "method": event.method,
        "verified_at": event.verified_at.isoformat() + "Z",
        "findings": event.findings,
        "supporting_evidence": event.supporting_evidence,
        "limitations": event.limitations,
    }


@router.get("", dependencies=[Depends(business_access)])
def verified_evidence(business_id: str, status: VerificationStatus | None = None,
                      kind: Literal["transaction", "invoice", "obligation"] | None = None,
                      search: str = Query("", max_length=160),
                      sort: Literal["recent", "date", "amount", "reference"] = "recent",
                      offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100)) -> dict:
    with SessionLocal() as db:
        _ready(db)
        source = RecordProvenance
        date = func.coalesce(Transaction.transaction_date, Invoice.issued_at)
        amount = func.coalesce(Transaction.amount_inr, Invoice.total_inr, Obligation.monthly_payment_inr)
        reference = func.coalesce(source.original_source_reference, Transaction.external_ref, Invoice.invoice_no)
        query = (latest_results(business_id)
                 .outerjoin(Transaction, and_(Transaction.id == source.transaction_id, Transaction.business_id == business_id))
                 .outerjoin(Invoice, and_(Invoice.id == source.invoice_id, Invoice.business_id == business_id))
                 .outerjoin(Obligation, and_(Obligation.id == source.obligation_id, Obligation.business_id == business_id))
                 .outerjoin(DataSource, and_(DataSource.id == source.source_id, DataSource.business_id == business_id)))
        if status is not None:
            query = query.where(VerificationEvent.status == status)
        if kind is not None:
            query = query.where({"transaction": source.transaction_id, "invoice": source.invoice_id,
                                 "obligation": source.obligation_id}[kind].is_not(None))
        if search.strip():
            search = search.strip()
            query = query.where(or_(
                reference.icontains(search, autoescape=True),
                DataSource.source_label.icontains(search, autoescape=True),
                source.source_id == search, source.transaction_id == search,
                source.invoice_id == search, source.obligation_id == search,
            ))
        order = {"recent": (), "date": (date.desc().nulls_last(),), "amount": (amount.desc().nulls_last(),),
                 "reference": (func.lower(reference).asc().nulls_last(),)}[sort]
        counts = status_counts(db, business_id)
        match_count = (db.scalar(query.with_only_columns(func.count()).select_from(RecordProvenance))
                       if kind or search else counts.get(status, 0) if status else sum(counts.values()))
        rows = db.execute(query.add_columns(date, amount, reference, DataSource.source_label)
                          .order_by(*order, VerificationEvent.id.desc()).offset(offset).limit(limit + 1)).all()
        return {
            "counts": counts,
            "matching_count": match_count,
            "items": [
                {
                    "provenance_id": source.id,
                    "business_id": source.business_id,
                    "record_id": record_id_of(source),
                    "record_type": "transaction" if source.transaction_id else "invoice" if source.invoice_id else "obligation",
                    "source_id": source.source_id,
                    "source_type": source.source_type,
                    "source_provider": source.source_provider,
                    "original_source_reference": source.original_source_reference,
                    "record_reference": record_reference,
                    "record_date": record_date.isoformat() if record_date else None,
                    "amount_inr": str(record_amount) if record_amount is not None else None,
                    "source_label": source_label,
                    "uploaded_at": source.uploaded_at.isoformat() + "Z" if source.uploaded_at else None,
                    "file_sha256": source.file_sha256,
                    "consent_reference": source.consent_reference,
                    "result": _event(event),
                } for source, event, record_date, record_amount, record_reference, source_label in rows[:limit]
            ],
            "next_offset": offset + limit if len(rows) > limit else None,
        }


@router.get("/{provenance_id}/history", dependencies=[Depends(business_access)])
def verification_history(business_id: str, provenance_id: str, after: int = Query(0, ge=0),
                         limit: int = Query(25, ge=1, le=100)) -> dict:
    with SessionLocal() as db:
        _ready(db)
        record = db.scalar(select(RecordProvenance.id).where(
            RecordProvenance.id == provenance_id, RecordProvenance.business_id == business_id,
        ))
        if record is None:
            raise HTTPException(404, "Evidence record not found.")
        events = db.scalars(select(VerificationEvent).where(
            VerificationEvent.provenance_id == record, VerificationEvent.id > after,
        ).order_by(VerificationEvent.id).limit(limit + 1)).all()
        return {"items": [_event(event) for event in events[:limit]],
                "next_after": events[limit - 1].id if len(events) > limit else None}


@router.post("/reconcile", dependencies=[Depends(owned_business)])
def reconcile_evidence(business_id: str) -> dict:
    with SessionLocal.begin() as db:
        _ready(db)
        # Serializes decisions with other reconciliation runs and transaction uploads.
        db.scalar(select(Business.id).where(Business.id == business_id).with_for_update())
        evidence = _calculate(business_id, db)
        changed = reconcile(db, business_id, evidence["findings"])
        db.flush()
        return {"records_updated": changed, "counts": status_counts(db, business_id)}
