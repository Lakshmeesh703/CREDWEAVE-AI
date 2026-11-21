from datetime import date
from decimal import Decimal

from app.services.evidence_dna import EvidenceRecord, calculate_evidence_dna


def record(record_id, kind, amount, day=1, period="2025-07", counterparty="cp-1"):
    return EvidenceRecord(
        record_id=record_id,
        source_id=f"source-{kind}",
        kind=kind,
        period=period,
        amount=Decimal(str(amount)),
        record_date=date.fromisoformat(f"{period}-{day:02d}"),
        counterparty_id=counterparty,
        direction="receivable" if kind == "invoice" else "credit",
    )


def test_exact_match_is_cross_source_consistency_not_verification():
    result = calculate_evidence_dna(
        [record("tx-1", "transaction", 100000, day=10)],
        [record("inv-1", "invoice", 100000)],
        expected_periods=["2025-07"],
    )
    assert result["evidence_consistency"]["score"] == 100
    assert result["verification_status"]["cross-source-consistent"] == 1
    assert result["verification_status"]["externally-verified"] == 0


def test_amount_and_date_tolerances_are_explicit():
    result = calculate_evidence_dna(
        [record("tx-1", "transaction", 102000, day=15)],
        [record("inv-1", "invoice", 100000)],
        expected_periods=["2025-07"],
    )
    assert result["evidence_consistency"]["matched"] == 0
    assert any(item["code"] == "UNMATCHED_INVOICE" for item in result["findings"])


def test_duplicate_candidates_and_missing_periods_are_reported():
    result = calculate_evidence_dna(
        [
            record("tx-1", "transaction", 100000),
            record("tx-2", "transaction", 100000),
        ],
        [record("inv-1", "invoice", 100000)],
        expected_periods=["2025-07", "2025-08"],
    )
    assert result["evidence_completeness"]["score"] == 50
    assert any(item["code"] == "DUPLICATE_RECORD_CANDIDATE" for item in result["findings"])
    assert all("fraud" not in item["explanation"].lower() for item in result["findings"])


def test_partial_or_unmatched_records_are_unknown_evidence():
    result = calculate_evidence_dna(
        [record("tx-1", "transaction", 19000, period="2025-12")],
        [record("inv-1", "invoice", 27000, period="2025-12")],
        expected_periods=["2025-12"],
    )
    assert result["verification_status"]["uploaded-only"] == 2
    assert "unknown evidence" in next(
        item["explanation"] for item in result["findings"] if item["code"] == "UNMATCHED_INVOICE"
    )


def test_contrasting_demo_profiles_produce_different_consistency_scores():
    complete_transactions = [
        record(f"tx-{month}", "transaction", 100000, day=10, period=f"2025-{month:02d}")
        for month in range(7, 13)
    ]
    complete_invoices = [
        record(f"inv-{month}", "invoice", 100000, period=f"2025-{month:02d}")
        for month in range(7, 13)
    ]
    incomplete_transactions = complete_transactions[:3] + [
        record("tx-partial", "transaction", 88000, day=10, period="2025-10")
    ]
    complete = calculate_evidence_dna(complete_transactions, complete_invoices, expected_periods=[f"2025-{month:02d}" for month in range(7, 13)])
    incomplete = calculate_evidence_dna(incomplete_transactions, complete_invoices, expected_periods=[f"2025-{month:02d}" for month in range(7, 13)])
    assert complete["evidence_consistency"]["score"] > incomplete["evidence_consistency"]["score"]
