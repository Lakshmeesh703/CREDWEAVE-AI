from fastapi import HTTPException
import pytest

from app.services.transaction_csv import parse_transactions

HEADER = "external_ref,transaction_date,amount_inr,direction,payment_channel,description,currency"
CREDIT = "a,2025-01-10,10.00,credit,upi,Receipt,INR"


def parse(lines, filename="statement.csv", content_type="text/csv"):
    return parse_transactions(("\n".join(lines) + "\n").encode(), filename, content_type)


@pytest.mark.parametrize(("rows", "status"), [
    ([HEADER, CREDIT, CREDIT], 422),
    ([HEADER, CREDIT.replace("2025-01-10", "20250110")], 422),
    ([HEADER, CREDIT.replace("2025-01-10", "2999-01-10")], 422),
    ([HEADER, CREDIT.replace("10.00", "-10.00")], 422),
    ([HEADER, CREDIT.replace("10.00", "NaN")], 422),
    ([HEADER, CREDIT.replace("10.00", "0.00")], 422),
    ([HEADER, CREDIT.replace("credit", "outgoing")], 422),
    ([HEADER, CREDIT.replace("Receipt", '"unclosed')], 422),
    ([HEADER, CREDIT.replace("Receipt", "embedded\x00control")], 422),
])
def test_malformed_or_impossible_records_are_rejected(rows, status):
    with pytest.raises(HTTPException) as exc:
        parse(rows)
    assert exc.value.status_code == status


def test_csv_type_and_format_are_validated():
    with pytest.raises(HTTPException) as exc:
        parse([HEADER, CREDIT], filename="statement.pdf", content_type="application/pdf")
    assert exc.value.status_code == 415


def test_split_columns_and_running_balances():
    header = HEADER.replace("amount_inr,direction", "debit_inr,credit_inr") + ",balance_inr"
    rows = parse([
        header,
        "b,2025-01-11,5.00,,upi,,INR,88.00",
        "a,2025-01-10,,10.00,upi,Receipt,INR,100.00",
    ])
    assert rows[0].direction == "debit"
    assert rows[1].amount_inr == 10
    assert {finding["code"] for finding in rows[0].findings} == {"MISSING_DESCRIPTION", "RUNNING_BALANCE_MISMATCH"}
    assert rows[1].findings == []
    with pytest.raises(HTTPException):
        parse([header, "b,2025-01-11,7.00,10.00,upi,Receipt,INR,88.00"])


def test_similar_rows_are_review_candidates():
    rows = parse([HEADER, CREDIT, CREDIT.replace("a,", "b,", 1)])
    assert [row.findings[0]["code"] for row in rows] == ["REPEATED_TRANSACTION", "REPEATED_TRANSACTION"]
