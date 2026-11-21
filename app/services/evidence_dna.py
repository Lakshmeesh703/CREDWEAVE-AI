from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Iterable, Sequence

RULE_VERSION = "evidence-dna.v1"
AMOUNT_TOLERANCE = Decimal("100.00")
AMOUNT_TOLERANCE_RATE = Decimal("0.01")
DATE_TOLERANCE_DAYS = 14


@dataclass(frozen=True)
class EvidenceRecord:
    record_id: str
    source_id: str
    kind: str
    period: str
    amount: Decimal | None = None
    record_date: date | None = None
    counterparty_id: str | None = None
    direction: str | None = None


@dataclass(frozen=True)
class EvidenceFinding:
    code: str
    severity: str
    explanation: str
    linked_source_ids: tuple[str, ...]
    record_ids: tuple[str, ...]
    amounts_inr: tuple[Decimal, ...]
    check_performed: str
    recommended_follow_up: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "explanation": self.explanation,
            "linked_source_ids": list(self.linked_source_ids),
            "record_ids": list(self.record_ids),
            "amounts_inr": [str(amount) for amount in self.amounts_inr],
            "check_performed": self.check_performed,
            "recommended_follow_up": self.recommended_follow_up,
            "rule_version": RULE_VERSION,
        }


def _period(value: date) -> str:
    return value.strftime("%Y-%m")


def _amount_matches(left: Decimal, right: Decimal) -> bool:
    difference = abs(left - right)
    return difference <= max(AMOUNT_TOLERANCE, abs(left) * AMOUNT_TOLERANCE_RATE)


def _date_matches(left: date, right: date) -> bool:
    return abs((left - right).days) <= DATE_TOLERANCE_DAYS


def _finding(
    code: str,
    severity: str,
    explanation: str,
    records: Iterable[EvidenceRecord],
    amounts: Iterable[Decimal] = (),
    check: str = "",
    follow_up: str = "",
) -> EvidenceFinding:
    record_list = list(records)
    return EvidenceFinding(
        code=code,
        severity=severity,
        explanation=explanation,
        linked_source_ids=tuple(sorted({record.source_id for record in record_list})),
        record_ids=tuple(record.record_id for record in record_list),
        amounts_inr=tuple(amounts),
        check_performed=check,
        recommended_follow_up=follow_up,
    )


def calculate_evidence_dna(
    transactions: Sequence[EvidenceRecord],
    invoices: Sequence[EvidenceRecord],
    *,
    expected_periods: Sequence[str] | None = None,
    reported_monthly_revenue_inr: Decimal | None = None,
) -> dict[str, Any]:
    """Return reproducible evidence metrics without inferring credit risk.

    Receivable invoices are compared with credit transactions only when both dates
    and amounts are available. An unmatched record is classified as uploaded-only,
    not suspicious. Existing links may be represented by ``kind='linked'`` records
    with the same invoice and transaction IDs encoded by the caller when desired;
    this pure function deliberately relies only on observable record fields.
    """
    all_periods = sorted({record.period for record in (*transactions, *invoices)})
    periods = list(expected_periods or all_periods)
    transaction_periods = {record.period for record in transactions}
    invoice_periods = {record.period for record in invoices}
    completed = sum(
        period in present
        for period in periods
        for present in (transaction_periods, invoice_periods)
    )
    completeness = round((completed / (len(periods) * 2)) * 100) if periods else 0

    candidate_transactions = [record for record in transactions if record.direction == "credit"]
    matched_invoice_ids: set[str] = set()
    matched_transaction_ids: set[str] = set()
    findings: list[EvidenceFinding] = []
    match_pairs: list[tuple[EvidenceRecord, EvidenceRecord]] = []

    for invoice in sorted(invoices, key=lambda item: item.record_id):
        candidates = [
            transaction for transaction in candidate_transactions
            if transaction.record_id not in matched_transaction_ids
            and transaction.record_date is not None
            and invoice.record_date is not None
            and invoice.amount is not None
            and transaction.amount is not None
            and _amount_matches(invoice.amount, transaction.amount)
            and _date_matches(invoice.record_date, transaction.record_date)
            and (invoice.counterparty_id is None or transaction.counterparty_id is None
                 or invoice.counterparty_id == transaction.counterparty_id)
        ]
        if candidates:
            transaction = sorted(
                candidates,
                key=lambda item: (abs(invoice.record_date - item.record_date).days, item.record_id),
            )[0]
            matched_invoice_ids.add(invoice.record_id)
            matched_transaction_ids.add(transaction.record_id)
            match_pairs.append((invoice, transaction))

    eligible_invoices = [invoice for invoice in invoices if invoice.amount is not None and invoice.record_date is not None]
    matched_count = len(match_pairs)
    consistency = round((matched_count / len(eligible_invoices)) * 100) if eligible_invoices else 0

    if match_pairs:
        for invoice, transaction in match_pairs:
            findings.append(_finding(
                "CROSS_SOURCE_MATCH",
                "info",
                "Invoice and receipt align within the configured amount and date tolerances. This supports consistency, not independent authentication of the underlying transaction.",
                (invoice, transaction),
                (invoice.amount or Decimal(0), transaction.amount or Decimal(0)),
                "Compared invoice total to a credit transaction within ₹100 or 1% and 14 calendar days.",
                "Retain the source documents and ask the lender to review the counterparties and context.",
            ))

    for invoice in eligible_invoices:
        if invoice.record_id not in matched_invoice_ids:
            findings.append(_finding(
                "UNMATCHED_INVOICE",
                "medium",
                "No comparable credit transaction was found in the available sources. This is unknown evidence, not a fraud conclusion.",
                (invoice,),
                (invoice.amount or Decimal(0),),
                "Searched available credit transactions using the configured amount, date, and counterparty tolerances.",
                "Request the missing payment source or ask the reviewer to document why the invoice remains unpaid or unavailable.",
            ))

    for transaction in candidate_transactions:
        if transaction.record_id not in matched_transaction_ids:
            findings.append(_finding(
                "UNMATCHED_PAYMENT",
                "medium",
                "A credit transaction has no comparable invoice in the available sources. This is an evidence gap, not an automatic adverse finding.",
                (transaction,),
                (transaction.amount or Decimal(0),),
                "Searched available receivable invoices using the configured amount, date, and counterparty tolerances.",
                "Request the related invoice or supporting sales record.",
            ))

    duplicate_groups: dict[tuple[str, str, Decimal, str | None], list[EvidenceRecord]] = defaultdict(list)
    for record in transactions:
        if record.amount is not None:
            duplicate_groups[(record.period, record.direction or "", record.amount, record.counterparty_id)].append(record)
    for records in duplicate_groups.values():
        if len(records) > 1:
            findings.append(_finding(
                "DUPLICATE_RECORD_CANDIDATE",
                "medium",
                "Multiple transactions share the same period, direction, amount, and counterparty. They are duplicate candidates, not proof of duplicate activity.",
                records,
                (records[0].amount or Decimal(0),),
                "Grouped transactions by period, direction, amount, and counterparty.",
                "Ask the reviewer to compare source references and retain only the supported record if appropriate.",
            ))
            consistency = max(0, consistency - 10)

    unexplained = len([finding for finding in findings if finding.code in {"UNMATCHED_INVOICE", "UNMATCHED_PAYMENT"}])
    verification = Counter({
        "uploaded-only": unexplained,
        "cross-source-consistent": matched_count,
        "externally-verified": 0,
        "disputed": len([finding for finding in findings if finding.code == "DUPLICATE_RECORD_CANDIDATE"]),
        "unavailable": max(0, len(periods) * 2 - completed),
    })
    if completeness >= 80 and consistency >= 80:
        confidence = ("high", "Broad period coverage and strong reconciliation quality support a high rule-based assessment confidence; this is not a statistical confidence interval.")
    elif completeness >= 60 and consistency >= 50:
        confidence = ("moderate", "Some expected evidence is present and comparable, but coverage or reconciliation gaps limit the rule-based assessment confidence.")
    else:
        confidence = ("limited", "Coverage or reconciliation gaps materially limit the rule-based assessment confidence; missing evidence remains unknown.")

    claim = {
        "reported_amount_inr": str(reported_monthly_revenue_inr) if reported_monthly_revenue_inr is not None else None,
        "observed_monthly_credit_inr": {},
        "status": "not_recorded" if reported_monthly_revenue_inr is None else "compared",
        "explanation": "The reported amount is compared with available credit receipts only; matching does not authenticate the transaction.",
    }
    monthly_totals: dict[str, Decimal] = defaultdict(Decimal)
    for transaction in candidate_transactions:
        if transaction.amount is not None:
            monthly_totals[transaction.period] += transaction.amount
    claim["observed_monthly_credit_inr"] = {period: str(monthly_totals[period]) for period in sorted(monthly_totals)}

    return {
        "rule_version": RULE_VERSION,
        "evidence_completeness": {"score": completeness, "denominator": len(periods) * 2, "expected_periods": periods},
        "evidence_consistency": {"score": consistency, "denominator": len(eligible_invoices), "matched": matched_count},
        "verification_status": dict(verification),
        "assessment_confidence": {"label": confidence[0], "rationale": confidence[1]},
        "claim_to_evidence": claim,
        "findings": [finding.as_dict() for finding in findings],
        "limitations": [
            "No external institution or document authenticity verification is performed.",
            "An unmatched record is not necessarily suspicious.",
            "Cross-source consistency is not independent authentication.",
        ],
    }
