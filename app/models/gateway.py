"""Immutable source records and append-only verification decisions."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.entities import BaseModel, new_id


class VerificationStatus(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    SOURCE_VERIFIED = "SOURCE_VERIFIED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    SIMULATED_SOURCE_VERIFIED = "SIMULATED_SOURCE_VERIFIED"


class RecordProvenance(BaseModel):
    __tablename__ = "record_provenance"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN transaction_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN invoice_id IS NULL THEN 0 ELSE 1 END + "
            "CASE WHEN obligation_id IS NULL THEN 0 ELSE 1 END) = 1",
            name="ck_provenance_one_record",
        ),
        CheckConstraint("source_type IN ('USER_UPLOAD', 'INSTITUTIONAL', 'SIMULATED', 'LEGACY_UNKNOWN')",
                        name="ck_provenance_source_type"),
        CheckConstraint("file_sha256 IS NULL OR length(file_sha256) = 64", name="ck_provenance_file_hash_length"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("data_sources.id"), index=True)
    transaction_id: Mapped[str | None] = mapped_column(ForeignKey("transactions.id", ondelete="CASCADE"), unique=True)
    invoice_id: Mapped[str | None] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), unique=True)
    obligation_id: Mapped[str | None] = mapped_column(ForeignKey("obligations.id", ondelete="CASCADE"), unique=True)
    source_type: Mapped[str] = mapped_column(String(24))
    source_provider: Mapped[str | None] = mapped_column(String(120))
    original_source_reference: Mapped[str | None] = mapped_column(String(100))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime)
    file_sha256: Mapped[str | None] = mapped_column(String(64))
    consent_reference: Mapped[str | None] = mapped_column(String(160))


class VerificationEvent(BaseModel):
    __tablename__ = "verification_events"
    __table_args__ = (
        CheckConstraint("status IN ('UNVERIFIED', 'PARTIALLY_SUPPORTED', 'SOURCE_VERIFIED', "
                        "'REQUIRES_REVIEW', 'SIMULATED_SOURCE_VERIFIED')", name="ck_verification_status"),
        CheckConstraint("(status <> 'SOURCE_VERIFIED' OR method = 'institutional_authentication') AND "
                        "(status <> 'SIMULATED_SOURCE_VERIFIED' OR method = 'simulated_fixture')",
                        name="ck_verification_source_method"),
        Index("ix_verification_history", "provenance_id", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provenance_id: Mapped[str] = mapped_column(ForeignKey("record_provenance.id", ondelete="CASCADE"))
    provenance: Mapped[RecordProvenance] = relationship()
    method: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30))
    verified_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    findings: Mapped[list[dict[str, str]]] = mapped_column(JSON)
    supporting_evidence: Mapped[list[dict[str, str]]] = mapped_column(JSON)
    limitations: Mapped[list[str]] = mapped_column(JSON)
