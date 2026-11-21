from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.db.session import Base as BaseModel


class ConsentStatus(StrEnum):
    GRANTED = "granted"
    PENDING = "pending"
    WITHDRAWN = "withdrawn"


class SourceKind(StrEnum):
    BANK = "bank"
    UPI = "upi"
    INVOICE = "invoice"
    SUPPLIER = "supplier"
    MANUAL = "manual"


class ParsingStatus(StrEnum):
    IMPORTED = "imported"
    PENDING = "pending"
    FAILED = "failed"


class TransactionDirection(StrEnum):
    CREDIT = "credit"
    DEBIT = "debit"


class PaymentChannel(StrEnum):
    BANK_TRANSFER = "bank_transfer"
    UPI = "upi"
    CASH = "cash"


class InvoiceDirection(StrEnum):
    RECEIVABLE = "receivable"
    PAYABLE = "payable"


class InvoiceStatus(StrEnum):
    OPEN = "open"
    PAID = "paid"
    PARTIAL = "partial"
    OVERDUE = "overdue"


class CounterpartyType(StrEnum):
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    OTHER = "other"


class MatchMethod(StrEnum):
    EXACT_REFERENCE = "exact_reference"
    AMOUNT_DATE = "amount_date"
    MANUAL = "manual"


class MatchStatus(StrEnum):
    MATCHED = "matched"
    PARTIAL = "partial"
    UNMATCHED = "unmatched"
    DISPUTED = "disputed"


class AssessmentStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    NEEDS_MORE_INFORMATION = "needs_more_information"
    REVIEWED = "reviewed"


def new_id() -> str:
    return str(uuid4())


class PortalAccount(BaseModel):
    __tablename__ = "portal_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="owner")


class PasswordRecovery(BaseModel):
    __tablename__ = "password_recovery"

    account_id: Mapped[str] = mapped_column(ForeignKey("portal_accounts.id", ondelete="CASCADE"), primary_key=True)
    question: Mapped[str] = mapped_column(String(160), nullable=False)
    answer_salt: Mapped[str] = mapped_column(String(32), nullable=False)
    answer_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    failed_attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    blocked_until: Mapped[int] = mapped_column(nullable=False, default=0)


class Business(BaseModel):
    __tablename__ = "businesses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("portal_accounts.id"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=False)
    operating_months: Mapped[int] = mapped_column(nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    consent_status: Mapped[ConsentStatus] = mapped_column(String(20), nullable=False)
    source_upload_consent: Mapped[bool | None] = mapped_column(nullable=True, default=None)
    passport_sharing_consent: Mapped[bool | None] = mapped_column(nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    sources: Mapped[list["DataSource"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    counterparties: Mapped[list["Counterparty"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    obligations: Mapped[list["Obligation"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    assessments: Mapped[list["Assessment"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )


class BusinessShare(BaseModel):
    __tablename__ = "business_shares"

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), primary_key=True)
    lender_id: Mapped[str] = mapped_column(ForeignKey("portal_accounts.id", ondelete="CASCADE"), primary_key=True, index=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DataSource(BaseModel):
    __tablename__ = "data_sources"
    __table_args__ = (UniqueConstraint("business_id", "file_hash", name="uq_source_file_hash"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    kind: Mapped[SourceKind] = mapped_column(String(20), nullable=False)
    synthetic: Mapped[bool] = mapped_column(nullable=False, default=True)
    source_label: Mapped[str] = mapped_column(String(160), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    parsing_status: Mapped[ParsingStatus] = mapped_column(String(20), nullable=False)
    business: Mapped[Business] = relationship(back_populates="sources")


class Transaction(BaseModel):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("business_id", "source_id", "external_ref", name="uq_transaction_external_ref"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    external_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount_inr: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    direction: Mapped[TransactionDirection] = mapped_column(String(10), nullable=False)
    counterparty_id: Mapped[str | None] = mapped_column(ForeignKey("counterparties.id"))
    payment_channel: Mapped[PaymentChannel] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    business: Mapped[Business] = relationship(back_populates="transactions")


class Invoice(BaseModel):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("business_id", "invoice_no", name="uq_invoice_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    invoice_no: Mapped[str] = mapped_column(String(100), nullable=False)
    issued_at: Mapped[date] = mapped_column(Date, nullable=False)
    due_at: Mapped[date] = mapped_column(Date, nullable=False)
    total_inr: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    counterparty_id: Mapped[str | None] = mapped_column(ForeignKey("counterparties.id"))
    direction: Mapped[InvoiceDirection] = mapped_column(String(20), nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(String(20), nullable=False)
    business: Mapped[Business] = relationship(back_populates="invoices")


class PaymentLink(BaseModel):
    __tablename__ = "payment_links"
    __table_args__ = (
        UniqueConstraint("invoice_id", "transaction_id", name="uq_payment_link_pair"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), nullable=False)
    linked_amount_inr: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    match_method: Mapped[MatchMethod] = mapped_column(String(30), nullable=False)
    match_status: Mapped[MatchStatus] = mapped_column(String(20), nullable=False)


class Counterparty(BaseModel):
    __tablename__ = "counterparties"
    __table_args__ = (UniqueConstraint("business_id", "identifier_masked", name="uq_counterparty_identifier"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("data_sources.id"))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    type: Mapped[CounterpartyType] = mapped_column(String(20), nullable=False)
    identifier_masked: Mapped[str] = mapped_column(String(80), nullable=False)
    business: Mapped[Business] = relationship(back_populates="counterparties")


class Obligation(BaseModel):
    __tablename__ = "obligations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    monthly_payment_inr: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(240), nullable=False)
    business: Mapped[Business] = relationship(back_populates="obligations")


class Assessment(BaseModel):
    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[AssessmentStatus] = mapped_column(String(20), nullable=False)
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    limitations_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    business: Mapped[Business] = relationship(back_populates="assessments")


class Review(BaseModel):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id"), nullable=False)
    reviewer_account_id: Mapped[str | None] = mapped_column(ForeignKey("portal_accounts.id"))
    reviewer_name_or_alias: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[ReviewStatus] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    checklist_json: Mapped[dict[str, bool]] = mapped_column(JSON, nullable=False, default=dict)
    rule_version: Mapped[str] = mapped_column(String(40), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
