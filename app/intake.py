import hashlib
import json
from os import getenv
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select

from app.auth import Principal, business_access, businesses_for, current_user, owned_business, owner
from app.db.session import SessionLocal
from app.models import (
    Business,
    Counterparty,
    DataSource,
    Invoice,
    Obligation,
    Transaction,
)
from app.models.entities import (
    CounterpartyType,
    InvoiceDirection,
    InvoiceStatus,
    ParsingStatus,
    PortalAccount,
    SourceKind,
)
from app.schemas.contracts import (
    BusinessCreate,
    BusinessResponse,
    BusinessUpdate,
    InvoiceResponse,
    TransactionResponse,
    CounterpartyResponse,
    ObligationResponse,
    DataSourceResponse,
)
from app.services.csv_intake import read_rows
from app.services.gateway import capture, finding, gateway_available
from app.services.transaction_csv import parse_transactions
from app.seed import seed as seed_synthetic

router = APIRouter(prefix="/api")
MAX_FILE_BYTES = 2 * 1024 * 1024

INVOICE_COLUMNS = {
    "invoice_no", "issued_at", "due_at", "total_inr", "direction",
    "status", "counterparty_name", "counterparty_type", "identifier_masked",
}
SUPPLIER_COLUMNS = {"counterparty_name", "identifier_masked"}
OBLIGATION_COLUMNS = {"monthly_payment_inr", "description"}


def _error(status: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail=detail)


def _parse_date(value: str, field: str, row: int) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise _error(422, f"Row {row}: {field} must be an ISO date (YYYY-MM-DD).") from exc


def _parse_amount(value: str, field: str, row: int) -> Decimal:
    try:
        amount = Decimal(value.strip())
    except (InvalidOperation, AttributeError) as exc:
        raise _error(422, f"Row {row}: {field} must be a valid INR amount.") from exc
    if not amount.is_finite() or amount < 0 or amount >= Decimal("1000000000000") or amount.as_tuple().exponent < -2:
        raise _error(422, f"Row {row}: {field} must be non-negative with at most 2 decimals.")
    return amount


def _counterparty(db, business_id: str, row: dict[str, str], row_number: int, fallback_type: CounterpartyType) -> str | None:
    name = row.get("counterparty_name", "")
    identifier = row.get("identifier_masked", "")
    if not name and not identifier:
        return None
    if len(name) > 160 or len(identifier) > 80:
        raise _error(422, f"Row {row_number}: counterparty name or masked identifier is too long.")
    if not name or not identifier:
        raise _error(422, f"Row {row_number}: counterparty_name and identifier_masked must be supplied together.")
    try:
        kind = CounterpartyType(row.get("counterparty_type") or fallback_type.value)
    except ValueError as exc:
        raise _error(422, f"Row {row_number}: invalid counterparty_type.") from exc
    existing = db.scalar(
        select(Counterparty).where(
            Counterparty.business_id == business_id,
            Counterparty.identifier_masked == identifier,
        )
    )
    if existing:
        return existing.id
    item = Counterparty(
        business_id=business_id,
        name=name,
        type=kind,
        identifier_masked=identifier,
    )
    db.add(item)
    db.flush()
    return item.id


async def _read_upload(upload: UploadFile) -> bytes:
    content = await upload.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise _error(413, "File exceeds the 2 MB import limit.")
    if not content:
        raise _error(422, "Uploaded file is empty.")
    return content


def _source_or_duplicate(db, business_id: str, kind: SourceKind, filename: str, content: bytes) -> DataSource:
    file_hash = hashlib.sha256(content).hexdigest()
    duplicate = db.scalar(
        select(DataSource).where(
            DataSource.business_id == business_id,
            DataSource.file_hash == file_hash,
        )
    )
    if duplicate:
        raise _error(409, f"This file was already imported as source {duplicate.id}.")
    source = DataSource(
        business_id=business_id,
        kind=kind,
        synthetic=False,
        source_label=filename.replace("\\", "/").rsplit("/", 1)[-1][:160] or "uploaded evidence",
        file_hash=file_hash,
        parsing_status=ParsingStatus.IMPORTED,
    )
    db.add(source)
    db.flush()
    return source


def _business_or_404(db, business_id: str) -> Business:
    business = db.get(Business, business_id)
    if not business:
        raise _error(404, "Business not found.")
    return business


def has_source_upload_consent(business: Business) -> bool:
    return (
        business.source_upload_consent
        if business.source_upload_consent is not None
        else getattr(business.consent_status, "value", business.consent_status) == "granted"
    )


@router.post("/businesses", response_model=BusinessResponse, status_code=201)
def create_business(payload: BusinessCreate, user: Principal = Depends(owner)) -> Business:
    with SessionLocal.begin() as db:
        values = payload.model_dump()
        if not user.demo:
            role = db.scalar(select(PortalAccount.role).where(PortalAccount.id == user.id).with_for_update())
            if role != "owner":
                raise _error(403, "Business Owner access required.")
            values["passport_sharing_consent"] = False
        business = Business(owner_id=None if user.demo else user.id, **values)
        db.add(business)
        db.flush()
        return business


@router.post("/demo/load")
def load_demo(user: Principal = Depends(current_user)) -> dict[str, Any]:
    if not user.demo or getenv("DEMO_MODE", "0").strip().lower() not in {"1", "true", "yes"}:
        raise HTTPException(status_code=403, detail="Synthetic demo loading is disabled; set DEMO_MODE=1 to enable it.")
    return {"businesses_seeded": seed_synthetic(simulate_gateway=True), "synthetic": True}


@router.get("/businesses", response_model=list[BusinessResponse])
def list_businesses(user: Principal = Depends(current_user)) -> list[Business]:
    with SessionLocal() as db:
        return list(db.scalars(businesses_for(user).order_by(Business.created_at.desc())))


@router.get("/businesses/{business_id}", response_model=BusinessResponse, dependencies=[Depends(business_access)])
def get_business(business_id: str) -> Business:
    with SessionLocal() as db:
        return _business_or_404(db, business_id)


@router.put("/businesses/{business_id}", response_model=BusinessResponse, dependencies=[Depends(owned_business)])
def edit_business(business_id: str, payload: BusinessUpdate) -> Business:
    with SessionLocal.begin() as db:
        business = _business_or_404(db, business_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(business, field, value)
        db.flush()
        return business


@router.patch("/businesses/{business_id}/upload-consent", response_model=BusinessResponse, dependencies=[Depends(owned_business)])
def set_upload_consent(business_id: str, granted: bool) -> Business:
    with SessionLocal.begin() as db:
        business = db.get(Business, business_id, with_for_update=True)
        if business is None:
            raise _error(404, "Business not found.")
        business.source_upload_consent = granted
        db.flush()
        return business


@router.get("/businesses/{business_id}/records", dependencies=[Depends(business_access)])
def list_records(business_id: str, kind: str, offset: int = Query(0, ge=0)) -> dict:
    record_types = {
        "transactions": (Transaction, TransactionResponse),
        "invoices": (Invoice, InvoiceResponse),
        "counterparties": (Counterparty, CounterpartyResponse),
        "obligations": (Obligation, ObligationResponse),
    }
    if kind not in record_types:
        raise _error(422, "Choose transactions, invoices, counterparties, or obligations.")
    model, contract = record_types[kind]
    page_size = 25
    with SessionLocal() as db:
        rows = db.scalars(select(model).where(model.business_id == business_id)
                          .order_by(model.id).offset(offset).limit(page_size + 1)).all()
        return {"items": [contract.model_validate(row).model_dump(mode="json") for row in rows[:page_size]],
                "next_offset": offset + page_size if len(rows) > page_size else None}


@router.get("/businesses/{business_id}/sources", response_model=list[DataSourceResponse], dependencies=[Depends(business_access)])
def list_sources(business_id: str) -> list[DataSource]:
    with SessionLocal() as db:
        _business_or_404(db, business_id)
        return list(db.scalars(select(DataSource).where(DataSource.business_id == business_id)))


@router.get("/businesses/{business_id}/records-summary", dependencies=[Depends(business_access)])
def records_summary(business_id: str) -> dict[str, Any]:
    with SessionLocal() as db:
        _business_or_404(db, business_id)
        models = {
            "transactions": Transaction,
            "invoices": Invoice,
            "obligations": Obligation,
            "counterparties": Counterparty,
            "sources": DataSource,
        }
        return {
            "business_id": business_id,
            "synthetic": bool(db.scalar(select(func.count()).select_from(DataSource).where(
                DataSource.business_id == business_id, DataSource.synthetic.is_(True)
            ))),
            "counts": {
                name: db.scalar(select(func.count()).select_from(model).where(model.business_id == business_id))
                for name, model in models.items()
            },
        }


@router.post("/businesses/{business_id}/imports/transactions", dependencies=[Depends(owned_business)])
async def import_transactions(business_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    content = await _read_upload(file)
    rows = parse_transactions(content, file.filename, file.content_type)
    with SessionLocal.begin() as db:
        business = db.get(Business, business_id, with_for_update=True)
        if business is None or not has_source_upload_consent(business):
            raise _error(403, "Source upload consent is required before importing evidence.")
        kind = SourceKind.UPI if all(row.payment_channel == "upi" for row in rows) else SourceKind.BANK
        source = _source_or_duplicate(db, business_id, kind, file.filename or "transactions.csv", content)
        references = set(db.scalars(select(Transaction.external_ref).where(Transaction.business_id == business_id)))
        # Similar rows across uploads require review, even when their references differ.
        days = [row.transaction_date for row in rows]
        existing = set(db.execute(
            select(Transaction.transaction_date, Transaction.amount_inr, Transaction.direction,
                   Transaction.payment_channel, Transaction.description, Counterparty.identifier_masked)
            .outerjoin(Counterparty, Counterparty.id == Transaction.counterparty_id)
            .where(Transaction.business_id == business_id, Transaction.transaction_date.between(min(days), max(days)))
        ))
        similar = {(day, amount, direction, channel, description.casefold(), identifier or "")
                   for day, amount, direction, channel, description, identifier in existing}
        tracked = []
        for row in rows:
            if row.external_ref in references:
                row.findings.append(finding("REFERENCE_IN_ANOTHER_UPLOAD", "The transaction reference also appears in an earlier upload."))
            if row.duplicate_key in similar:
                row.findings.append(finding("TRANSACTION_IN_ANOTHER_UPLOAD", "A similar transaction appears in an earlier upload."))
            transaction = Transaction(
                business_id=business_id, source_id=source.id, external_ref=row.external_ref,
                transaction_date=row.transaction_date, amount_inr=row.amount_inr,
                direction=row.direction, payment_channel=row.payment_channel, description=row.description,
                currency="INR", counterparty_id=_counterparty(db, business_id, row.counterparty, row.row_number, CounterpartyType.OTHER),
            )
            db.add(transaction)
            tracked.append((transaction, row))
        db.flush()
        if gateway_available(db):
            for record, row in tracked:
                capture(db, record, "transaction", source=source, reference=row.external_ref,
                        provider=row.provider, findings=row.findings)
        return {"source_id": source.id, "accepted_rows": len(rows), "synthetic": False,
                "requires_review": sum(bool(row.findings) for row in rows)}


@router.post("/businesses/{business_id}/imports/invoices", dependencies=[Depends(owned_business)])
async def import_invoices(business_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    content = await _read_upload(file)
    rows = read_rows(content, {"invoice_no", "issued_at", "due_at", "total_inr", "direction", "status"}, INVOICE_COLUMNS)
    with SessionLocal.begin() as db:
        if not has_source_upload_consent(_business_or_404(db, business_id)):
            raise _error(403, "Source upload consent is required before importing evidence.")
        source = _source_or_duplicate(db, business_id, SourceKind.INVOICE, file.filename or "invoices.csv", content)
        tracked = []
        for row_number, row in enumerate(rows, start=2):
            try:
                direction = InvoiceDirection(row["direction"])
                status = InvoiceStatus(row["status"])
            except ValueError as exc:
                raise _error(422, f"Row {row_number}: invalid invoice direction or status.") from exc
            if len(row["invoice_no"]) > 100:
                raise _error(422, f"Row {row_number}: invoice_no is too long.")
            invoice = Invoice(
                business_id=business_id, source_id=source.id, invoice_no=row["invoice_no"],
                issued_at=_parse_date(row["issued_at"], "issued_at", row_number),
                due_at=_parse_date(row["due_at"], "due_at", row_number),
                total_inr=_parse_amount(row["total_inr"], "total_inr", row_number),
                direction=direction, status=status,
                counterparty_id=_counterparty(
                    db, business_id, row, row_number,
                    CounterpartyType.SUPPLIER if direction is InvoiceDirection.PAYABLE else CounterpartyType.CUSTOMER,
                ),
            )
            db.add(invoice)
            tracked.append(invoice)
        db.flush()
        if gateway_available(db):
            for invoice in tracked:
                capture(db, invoice, "invoice", source=source, reference=invoice.invoice_no)
        return {"source_id": source.id, "accepted_rows": len(rows), "synthetic": False}


@router.post("/businesses/{business_id}/imports/suppliers", dependencies=[Depends(owned_business)])
async def import_suppliers(business_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    content = await _read_upload(file)
    rows = read_rows(content, SUPPLIER_COLUMNS, SUPPLIER_COLUMNS)
    identifiers = {row["identifier_masked"] for row in rows}
    if len(identifiers) != len(rows):
        raise _error(422, "Each masked supplier identifier must be unique within the file.")
    with SessionLocal.begin() as db:
        if not has_source_upload_consent(_business_or_404(db, business_id)):
            raise _error(403, "Source upload consent is required before importing evidence.")
        source = _source_or_duplicate(db, business_id, SourceKind.SUPPLIER, file.filename or "suppliers.csv", content)
        for row_number, row in enumerate(rows, start=2):
            supplier_id = _counterparty(db, business_id, row, row_number, CounterpartyType.SUPPLIER)
            supplier = db.get(Counterparty, supplier_id)
            if supplier.type == CounterpartyType.CUSTOMER:
                raise _error(422, f"Row {row_number}: the masked identifier is already assigned to a customer.")
            supplier.type = CounterpartyType.SUPPLIER
            supplier.name = row["counterparty_name"]
            supplier.source_id = source.id
        return {"source_id": source.id, "accepted_rows": len(rows), "synthetic": False}


@router.post("/businesses/{business_id}/imports/obligations", dependencies=[Depends(owned_business)])
async def import_obligations(business_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    content = await _read_upload(file)
    try:
        if (file.filename or "").lower().endswith(".json"):
            payload = json.loads(content)
            rows = payload if isinstance(payload, list) else payload.get("obligations")
            if not isinstance(rows, list):
                raise ValueError
            rows = [{str(k): str(v) for k, v in row.items()} for row in rows]
        else:
            rows = read_rows(content, OBLIGATION_COLUMNS, OBLIGATION_COLUMNS)
    except (json.JSONDecodeError, AttributeError, ValueError) as exc:
        raise _error(422, "Obligations JSON must be an array or an object with an obligations array.") from exc
    if not rows:
        raise _error(422, "Obligations import must contain at least one row.")
    with SessionLocal.begin() as db:
        if not has_source_upload_consent(_business_or_404(db, business_id)):
            raise _error(403, "Source upload consent is required before importing evidence.")
        source = _source_or_duplicate(db, business_id, SourceKind.MANUAL, file.filename or "obligations.json", content)
        tracked = []
        for row_number, row in enumerate(rows, start=2):
            if set(row) - OBLIGATION_COLUMNS or not OBLIGATION_COLUMNS.issubset(row):
                raise _error(422, f"Row {row_number}: expected monthly_payment_inr and description only.")
            if not row["description"] or len(row["description"]) > 240:
                raise _error(422, f"Row {row_number}: description must contain 1–240 characters.")
            obligation = Obligation(
                business_id=business_id,
                monthly_payment_inr=_parse_amount(row["monthly_payment_inr"], "monthly_payment_inr", row_number),
                description=row["description"],
            )
            db.add(obligation)
            tracked.append(obligation)
        db.flush()
        if gateway_available(db):
            for obligation in tracked:
                capture(db, obligation, "obligation", source=source)
        return {"source_id": source.id, "accepted_rows": len(rows), "synthetic": False}
