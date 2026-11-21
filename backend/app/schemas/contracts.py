from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.entities import (
    AssessmentStatus,
    ConsentStatus,
    CounterpartyType,
    InvoiceDirection,
    InvoiceStatus,
    MatchMethod,
    MatchStatus,
    PaymentChannel,
    ParsingStatus,
    ReviewStatus,
    SourceKind,
    TransactionDirection,
)


class ContractModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class BusinessDetails(ContractModel):
    name: str = Field(min_length=1, max_length=160)
    sector: str = Field(min_length=1, max_length=100)
    operating_months: int = Field(ge=0, le=2147483647)
    city: str = Field(min_length=1, max_length=100)


class BusinessCreate(BusinessDetails):
    consent_status: ConsentStatus
    source_upload_consent: bool | None = None
    passport_sharing_consent: bool | None = None


class BusinessUpdate(BusinessDetails):
    source_upload_consent: bool = False


class BusinessResponse(BusinessCreate):
    id: str
    created_at: datetime


class DataSourceResponse(ContractModel):
    id: str
    business_id: str
    kind: SourceKind
    synthetic: bool
    source_label: str
    imported_at: datetime
    file_hash: str
    parsing_status: ParsingStatus


class TransactionResponse(ContractModel):
    id: str
    business_id: str
    source_id: str
    external_ref: str
    transaction_date: date
    amount_inr: Decimal = Field(ge=0)
    direction: TransactionDirection
    counterparty_id: str | None
    payment_channel: PaymentChannel
    description: str
    currency: str = Field(pattern=r"^[A-Z]{3}$")


class InvoiceResponse(ContractModel):
    id: str
    business_id: str
    source_id: str
    invoice_no: str
    issued_at: date
    due_at: date
    total_inr: Decimal = Field(ge=0)
    counterparty_id: str | None
    direction: InvoiceDirection
    status: InvoiceStatus


class PaymentLinkResponse(ContractModel):
    id: str
    business_id: str
    invoice_id: str
    transaction_id: str
    linked_amount_inr: Decimal = Field(ge=0)
    match_method: MatchMethod
    match_status: MatchStatus


class CounterpartyResponse(ContractModel):
    id: str
    business_id: str
    source_id: str | None
    name: str
    type: CounterpartyType
    identifier_masked: str


class ObligationResponse(ContractModel):
    id: str
    business_id: str
    monthly_payment_inr: Decimal = Field(ge=0)
    description: str


class AssessmentResponse(ContractModel):
    id: str
    business_id: str
    created_at: datetime
    rule_version: str
    status: AssessmentStatus
    snapshot_json: dict
    limitations_json: list[str]


class ReviewResponse(ContractModel):
    id: str
    assessment_id: str
    reviewer_name_or_alias: str
    status: ReviewStatus
    reason: str
    checklist_json: dict[str, bool]
    rule_version: str
    updated_at: datetime


class EvidenceFindingResponse(ContractModel):
    code: str
    severity: str
    explanation: str
    linked_source_ids: list[str]
    record_ids: list[str]
    amounts_inr: list[Decimal]
    check_performed: str
    recommended_follow_up: str
    rule_version: str


class EvidenceDnaResponse(ContractModel):
    business_id: str
    business_name: str
    rule_version: str
    evidence_completeness: dict
    evidence_consistency: dict
    verification_status: dict[str, int]
    assessment_confidence: dict[str, str]
    claim_to_evidence: dict
    findings: list[EvidenceFindingResponse]
    limitations: list[str]
    provenance: dict
