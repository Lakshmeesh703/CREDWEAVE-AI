"""Normalize transaction CSVs and distinguish invalid input from review signals."""

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.models.entities import PaymentChannel, TransactionDirection
from app.services.csv_intake import read_rows
from app.services.gateway import finding

COMMON = {"external_ref", "transaction_date", "payment_channel", "description", "currency"}
CANONICAL = {"amount_inr", "direction"}
BANK_SPLIT = {"debit_inr", "credit_inr"}
OPTIONAL = {"counterparty_name", "counterparty_type", "identifier_masked", "balance_inr", "source_provider"}
CSV_MEDIA_TYPES = {"", "text/csv", "text/plain", "application/csv", "application/octet-stream", "application/vnd.ms-excel"}


@dataclass
class NormalizedTransaction:
    row_number: int
    external_ref: str
    transaction_date: date
    amount_inr: Decimal
    direction: TransactionDirection
    payment_channel: PaymentChannel
    description: str
    balance: Decimal | None
    provider: str | None
    counterparty: dict[str, str]
    findings: list[dict[str, str]] = field(default_factory=list)

    @property
    def duplicate_key(self) -> tuple:
        return (
            self.transaction_date, self.amount_inr, self.direction, self.payment_channel,
            self.description.casefold(), self.counterparty.get("identifier_masked", ""),
        )


def _invalid(row: int, detail: str) -> HTTPException:
    return HTTPException(422, f"Row {row}: {detail}")


def _money(value: str, row: int, field_name: str, *, signed: bool = False) -> Decimal:
    if not re.fullmatch(r"-?(?:[0-9]{1,12}(?:\.[0-9]{0,2})?|\.[0-9]{1,2})", value):
        raise _invalid(row, f"{field_name} must be an INR amount with at most 2 decimals.")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise _invalid(row, f"{field_name} must be a valid INR amount.") from exc
    if not signed and amount < 0:
        raise _invalid(row, f"{field_name} must be non-negative.")
    return amount


def _normalize(row: dict[str, str], row_number: int, today: date) -> NormalizedTransaction:
    ref = row["external_ref"]
    if not ref or len(ref) > 100:
        raise _invalid(row_number, "external_ref must contain 1–100 characters.")
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["transaction_date"]):
            raise ValueError
        transaction_date = date.fromisoformat(row["transaction_date"])
    except ValueError as exc:
        raise _invalid(row_number, "transaction_date must be an ISO date (YYYY-MM-DD).") from exc
    if transaction_date > today:
        raise _invalid(row_number, "transaction_date cannot be in the future.")
    if row["currency"].upper() != "INR":
        raise _invalid(row_number, "only INR is supported.")
    try:
        channel = PaymentChannel(row["payment_channel"].lower())
    except ValueError as exc:
        raise _invalid(row_number, "invalid payment_channel.") from exc
    if "amount_inr" in row:
        amount = _money(row["amount_inr"], row_number, "amount_inr")
        try:
            direction = TransactionDirection(row["direction"].lower())
        except ValueError as exc:
            raise _invalid(row_number, "direction must be debit or credit.") from exc
        if amount == 0:
            raise _invalid(row_number, "amount_inr must be positive.")
    else:
        debit = _money(row["debit_inr"] or "0", row_number, "debit_inr")
        credit = _money(row["credit_inr"] or "0", row_number, "credit_inr")
        if bool(debit) == bool(credit):
            raise _invalid(row_number, "exactly one of debit_inr or credit_inr must be positive.")
        amount = debit or credit
        direction = TransactionDirection.DEBIT if debit else TransactionDirection.CREDIT
    provider = row.get("source_provider") or None
    if provider and len(provider) > 120:
        raise _invalid(row_number, "source_provider cannot exceed 120 characters.")
    description = row["description"]
    if len(description) > 1000:
        raise _invalid(row_number, "description cannot exceed 1,000 characters.")
    balance = _money(row["balance_inr"], row_number, "balance_inr", signed=True) if row.get("balance_inr") else None
    item = NormalizedTransaction(row_number, ref, transaction_date, amount, direction, channel, description, balance,
                                 provider, {key: row[key] for key in ("counterparty_name", "counterparty_type",
                                                                       "identifier_masked") if key in row})
    if not description:
        item.findings.append(finding("MISSING_DESCRIPTION", "This transaction is missing a description."))
    return item


def _check_running_balances(items: list[NormalizedTransaction]) -> None:
    if not any(item.balance is not None for item in items):
        return
    if len({item.provider for item in items}) > 1:
        for item in items:
            item.findings.append(finding("MIXED_BALANCE_PROVIDERS", "Running balances span multiple declared sources. Review each statement separately."))
        return
    days = [item.transaction_date for item in items]
    if days == sorted(days):
        ordered = items
    elif days == sorted(days, reverse=True):
        ordered = list(reversed(items))
    else:
        for item in items:
            item.findings.append(finding("UNORDERED_BALANCE", "Statement dates are out of order, so running balances could not be checked."))
        return
    for item in ordered:
        if item.balance is None:
            item.findings.append(finding("MISSING_RUNNING_BALANCE", "The running balance is missing from this statement row."))
    for previous, current in zip(ordered, ordered[1:]):
        if previous.balance is None or current.balance is None:
            continue
        delta = current.amount_inr if current.direction == TransactionDirection.CREDIT else -current.amount_inr
        if previous.balance + delta != current.balance:
            current.findings.append(finding("RUNNING_BALANCE_MISMATCH", "The previous balance plus this transaction does not equal the supplied balance."))


def parse_transactions(content: bytes, filename: str | None, content_type: str | None) -> list[NormalizedTransaction]:
    media_type = (content_type or "").split(";", 1)[0].strip().lower()
    if not (filename or "").lower().endswith(".csv") or media_type not in CSV_MEDIA_TYPES:
        raise HTTPException(415, "Upload a transaction file in CSV format.")
    rows = read_rows(content, COMMON, COMMON | CANONICAL | BANK_SPLIT | OPTIONAL, allow_blank={"description"})
    fields = rows[0].keys()
    if not (CANONICAL <= fields and not BANK_SPLIT & fields or BANK_SPLIT <= fields and not CANONICAL & fields):
        raise HTTPException(422, "Include amount_inr and direction, or debit_inr and credit_inr.")
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    items = [_normalize(row, number, today) for number, row in enumerate(rows, start=2)]
    seen = set()
    for item in items:
        if item.external_ref in seen:
            raise _invalid(item.row_number, "external_ref appears more than once in the file.")
        seen.add(item.external_ref)
    repeated = Counter(item.duplicate_key for item in items)
    for item in items:
        if repeated[item.duplicate_key] > 1:
            item.findings.append(finding("REPEATED_TRANSACTION", "Multiple rows share the same date, amount, direction, and transaction details."))
    _check_running_balances(items)
    return items
