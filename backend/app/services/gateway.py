"""Source attribution and verification decisions shared by intake and assessments."""

from collections import defaultdict
import re
from typing import Any

from sqlalchemy import false, func, inspect, select
from sqlalchemy.orm import Session

from app.models.entities import DataSource, Invoice, Obligation, Transaction
from app.models.gateway import RecordProvenance, VerificationEvent, VerificationStatus

CSV_LIMITATIONS = ["Validation of uploaded files does not establish authenticity or independent confirmation."]
MATCH_LIMITATIONS = ["Invoice and receipt matching supports consistency between available records. It does not establish authenticity."]
LEGACY_LIMITATIONS = ["Historical source metadata may be incomplete. No independent verification is recorded."]
SIMULATED_LIMITATIONS = ["Synthetic demo only. No bank or other institution was contacted."]
MODELS = ((Transaction, "transaction", "external_ref"), (Invoice, "invoice", "invoice_no"), (Obligation, "obligation", None))


def finding(code: str, reason: str) -> dict[str, str]:
    return {"code": code, "reason": reason}


def gateway_available(db: Session) -> bool:
    if db.bind.dialect.name == "sqlite":
        return True
    return inspect(db.connection()).has_table(VerificationEvent.__tablename__)


def capture(db: Session, record, kind: str, *, source: DataSource | None = None,
            reference: str | None = None, provider: str | None = None,
            findings: list[dict[str, str]] | None = None, historical: bool = False,
            simulated_verification: bool = False) -> RecordProvenance:
    if source is not None and source.business_id != record.business_id:
        raise ValueError("Provenance source and record must belong to the same business.")
    if simulated_verification and (kind != "transaction" or source is None or not source.synthetic):
        raise ValueError("Only an explicitly synthetic transaction source can be simulated.")
    synthetic = bool(source and source.synthetic)
    provenance = RecordProvenance(
        business_id=record.business_id,
        source_id=source.id if source else None,
        source_type="SIMULATED" if synthetic else "USER_UPLOAD" if source else "LEGACY_UNKNOWN",
        source_provider="CredWeave synthetic fixture" if synthetic else provider,
        original_source_reference=reference,
        uploaded_at=source.imported_at if source and not synthetic else None,
        file_sha256=source.file_hash if source and re.fullmatch(r"[0-9a-f]{64}", source.file_hash) else None,
        **{f"{kind}_id": record.id},
    )
    db.add(provenance)
    status = VerificationStatus.REQUIRES_REVIEW if findings else VerificationStatus.UNVERIFIED
    if simulated_verification:
        status = VerificationStatus.SIMULATED_SOURCE_VERIFIED
        method, limits = "simulated_fixture", SIMULATED_LIMITATIONS
        findings = [finding("DEMO_MOCK_SOURCE", "The record was seeded by the isolated mock institutional source.")]
    elif historical:
        method, limits = "historical_backfill", LEGACY_LIMITATIONS
        findings = [finding("LEGACY_RECORD", "Original validation results were not recorded.")]
    else:
        method, limits = "upload_validation", CSV_LIMITATIONS
    db.add(VerificationEvent(provenance=provenance, status=status, method=method,
                             findings=findings or [finding("UPLOADED_ONLY", "No corroborating evidence has been recorded.")],
                             supporting_evidence=[], limitations=limits))
    return provenance


def backfill(db: Session, business_ids: list[str] | None = None, *, simulate_demo: bool = False) -> None:
    for model, kind, ref in MODELS:
        source_id = getattr(model, "source_id", None)
        query = select(model, DataSource).outerjoin(
            DataSource, (DataSource.id == source_id) & (DataSource.business_id == model.business_id)
            if source_id is not None else false(),
        ).where(~select(RecordProvenance.id).where(getattr(RecordProvenance, f"{kind}_id") == model.id).exists())
        if business_ids is not None:
            query = query.where(model.business_id.in_(business_ids))
        for batch in db.execute(query).yield_per(250).partitions(250):
            for record, source in batch:
                capture(db, record, kind, source=source, reference=getattr(record, ref) if ref else None,
                        historical=True, simulated_verification=bool(simulate_demo and kind == "transaction" and source and source.synthetic))
            db.flush()


def latest_results(business_id: str):
    latest = (
        select(VerificationEvent.provenance_id, func.max(VerificationEvent.id).label("event_id"))
        .join(RecordProvenance).where(RecordProvenance.business_id == business_id)
        .group_by(VerificationEvent.provenance_id).subquery()
    )
    return select(RecordProvenance, VerificationEvent).join(latest, latest.c.provenance_id == RecordProvenance.id).join(
        VerificationEvent, VerificationEvent.id == latest.c.event_id,
    )


def status_counts(db: Session, business_id: str) -> dict[str, int]:
    query = latest_results(business_id).subquery()
    return dict(db.execute(select(query.c.status, func.count()).group_by(query.c.status)).all())


def record_id_of(provenance: RecordProvenance) -> str:
    return provenance.transaction_id or provenance.invoice_id or provenance.obligation_id


def reconcile(db: Session, business_id: str, evidence_findings: list[dict[str, Any]]) -> int:
    current = {record_id_of(source): (source, event) for source, event in db.execute(latest_results(business_id))}
    supporting = defaultdict(list)
    review = defaultdict(list)
    for item in evidence_findings:
        ids = item["record_ids"]
        if item["code"] == "CROSS_SOURCE_MATCH" and len(ids) == 2 and all(record_id in current for record_id in ids):
            left, right = ids
            if current[left][0].source_id != current[right][0].source_id:
                supporting[left].append(right)
                supporting[right].append(left)
        elif item["code"] == "DUPLICATE_RECORD_CANDIDATE":
            for record_id in ids:
                review[record_id].append(finding(item["code"], item["explanation"]))

    changed = 0
    for record_id, (source, previous) in current.items():
        if previous.status in {VerificationStatus.SOURCE_VERIFIED, VerificationStatus.SIMULATED_SOURCE_VERIFIED,
                               VerificationStatus.REQUIRES_REVIEW}:
            continue
        refs = [{"record_id": ref, "source_id": current[ref][0].source_id}
                for ref in sorted(supporting[record_id]) if current[ref][0].source_id]
        if review[record_id]:
            status, reasons = VerificationStatus.REQUIRES_REVIEW, review[record_id]
        elif refs:
            status = VerificationStatus.PARTIALLY_SUPPORTED
            reasons = [finding("CROSS_SOURCE_MATCH", "An invoice and credit transaction align under the Evidence DNA matching rules.")]
        elif previous.status == VerificationStatus.PARTIALLY_SUPPORTED:
            status = VerificationStatus.UNVERIFIED
            reasons = [finding("NO_CURRENT_MATCH", "Current matching rules did not find the previous corroborating record.")]
        else:
            continue
        if previous.status == status and previous.findings == reasons and previous.supporting_evidence == refs:
            continue
        db.add(VerificationEvent(provenance_id=source.id, method="evidence_dna_reconciliation",
                                 status=status, findings=reasons, supporting_evidence=refs, limitations=MATCH_LIMITATIONS))
        changed += 1
    return changed
