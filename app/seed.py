"""Seed the fixed, fully synthetic demonstration dataset."""

import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import delete, select

from app.db.session import Base, GATEWAY_TABLES, SessionLocal, database_url, engine
from app.models import (
    Assessment,
    Business,
    Counterparty,
    DataSource,
    Invoice,
    Obligation,
    PaymentLink,
    Review,
    Transaction,
)
from app.models.entities import (
    ConsentStatus,
    CounterpartyType,
    InvoiceDirection,
    InvoiceStatus,
    MatchMethod,
    MatchStatus,
    PaymentChannel,
    ParsingStatus,
    SourceKind,
    TransactionDirection,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT / "demo" / "demo_data.json"


def stable_id(key: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"credweave-ai:{key}"))


def add_source(db, business_id: str, key: str, kind: SourceKind, label: str) -> DataSource:
    item = DataSource(
        id=stable_id(key),
        business_id=business_id,
        kind=kind,
        synthetic=True,
        source_label=f"SYNTHETIC - {label}",
        imported_at=datetime(2026, 1, 1, 9),
        file_hash=f"synthetic-sha256-{stable_id(key).replace('-', '')}",
        parsing_status=ParsingStatus.IMPORTED,
    )
    db.add(item)
    return item


def seed(*, simulate_gateway: bool = False) -> int:
    config = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    if config.get("synthetic") is not True or config.get("currency") != "INR":
        raise ValueError("The fixture must be explicitly synthetic and denominated in INR.")

    tables = Base.metadata.sorted_tables
    if engine.dialect.name == "postgresql":
        if simulate_gateway:
            raise ValueError("Simulated source verification is available only on the isolated demo database.")
        tables = [table for table in tables if table.name not in GATEWAY_TABLES]
    Base.metadata.create_all(bind=engine, tables=tables)
    demo_business_ids = [stable_id(spec["key"]) for spec in config["businesses"]]
    with SessionLocal.begin() as db:
        demo_assessment_ids = select(Assessment.id).where(
            Assessment.business_id.in_(demo_business_ids)
        )
        db.execute(delete(Review).where(Review.assessment_id.in_(demo_assessment_ids)))
        for model in (PaymentLink, Transaction, Invoice, Obligation, Counterparty, DataSource, Assessment):
            db.execute(delete(model).where(model.business_id.in_(demo_business_ids)))
        db.execute(delete(Business).where(Business.id.in_(demo_business_ids)))

        for spec in config["businesses"]:
            business_id = stable_id(spec["key"])
            db.add(
                Business(
                    id=business_id,
                    name=spec["name"],
                    sector=spec["sector"],
                    operating_months=spec["operating_months"],
                    city=spec["city"],
                    consent_status=ConsentStatus(spec["consent_status"]),
                    created_at=datetime(2026, 1, 1, 9),
                )
            )
            bank = add_source(db, business_id, f"{spec['key']}-bank", SourceKind.BANK, "simulated bank statement")
            upi = add_source(db, business_id, f"{spec['key']}-upi", SourceKind.UPI, "simulated UPI export")
            invoice_source = add_source(db, business_id, f"{spec['key']}-invoices", SourceKind.INVOICE, "invoice register")

            counterparties = {}
            for item in spec["customers"] + spec["suppliers"]:
                counterparty = Counterparty(
                    id=stable_id(item["key"]),
                    business_id=business_id,
                    name=f"SYNTHETIC - {item['name']}",
                    type=CounterpartyType(item["type"]),
                    identifier_masked=item["identifier_masked"],
                )
                db.add(counterparty)
                counterparties[item["key"]] = counterparty

            for index, item in enumerate(spec["obligations"]):
                db.add(
                    Obligation(
                        id=stable_id(f"{spec['key']}-obligation-{index}"),
                        business_id=business_id,
                        monthly_payment_inr=Decimal(str(item["monthly_payment_inr"])),
                        description=f"SYNTHETIC - {item['description']}",
                    )
                )

            db.flush()
            first_month = date(2025, 7, 1)
            for month_index in range(6):
                month = first_month.replace(month=7 + month_index)
                customer_key = spec["customers"][month_index % len(spec["customers"])]["key"]
                supplier_key = spec["suppliers"][0]["key"]
                amount = Decimal("100000") if month_index % 2 == 0 else Decimal("96000")
                paid = spec["quality_profile"] == "more-complete" or month_index < 3
                invoice = Invoice(
                    id=stable_id(f"{spec['key']}-invoice-{month_index}"),
                    business_id=business_id,
                    source_id=invoice_source.id,
                    invoice_no=f"SYN-{spec['key'][-1].upper()}-{month:%Y%m}",
                    issued_at=month,
                    due_at=month + timedelta(days=30),
                    total_inr=amount,
                    counterparty_id=counterparties[customer_key].id,
                    direction=InvoiceDirection.RECEIVABLE,
                    status=InvoiceStatus.PAID if paid else InvoiceStatus.OPEN,
                )
                db.add(invoice)
                transaction = Transaction(
                    id=stable_id(f"{spec['key']}-sale-{month_index}"),
                    business_id=business_id,
                    source_id=bank.id,
                    external_ref=f"SYN-SALE-{spec['key'][-1].upper()}-{month:%Y%m}",
                    transaction_date=month + timedelta(days=10),
                    amount_inr=amount if paid else amount - Decimal("12000"),
                    direction=TransactionDirection.CREDIT,
                    counterparty_id=counterparties[customer_key].id,
                    payment_channel=PaymentChannel.BANK_TRANSFER,
                    description="SYNTHETIC customer receipt",
                    currency="INR",
                )
                db.add(transaction)
                db.flush()
                if paid:
                    db.add(
                        PaymentLink(
                            id=stable_id(f"{spec['key']}-link-{month_index}"),
                            business_id=business_id,
                            invoice_id=invoice.id,
                            transaction_id=transaction.id,
                            linked_amount_inr=transaction.amount_inr,
                            match_method=MatchMethod.EXACT_REFERENCE,
                            match_status=MatchStatus.MATCHED,
                        )
                    )
                db.add(
                    Transaction(
                        id=stable_id(f"{spec['key']}-supplier-{month_index}"),
                        business_id=business_id,
                        source_id=upi.id,
                        external_ref=f"SYN-SUP-{spec['key'][-1].upper()}-{month:%Y%m}",
                        transaction_date=month + timedelta(days=15),
                        amount_inr=Decimal("42000") if month_index % 3 == 0 else Decimal("36000"),
                        direction=TransactionDirection.DEBIT,
                        counterparty_id=counterparties[supplier_key].id,
                        payment_channel=PaymentChannel.UPI,
                        description="SYNTHETIC supplier payment",
                        currency="INR",
                    )
                )

            if spec["quality_profile"] == "more-complete":
                for source in (bank, upi):
                    db.add(
                        Transaction(
                            id=stable_id(f"{spec['key']}-duplicate-{source.kind}"),
                            business_id=business_id,
                            source_id=source.id,
                            external_ref="SYN-DUPLICATE-001",
                            transaction_date=date(2025, 9, 18),
                            amount_inr=Decimal("12500"),
                            direction=TransactionDirection.CREDIT,
                            counterparty_id=counterparties[spec["customers"][0]["key"]].id,
                            payment_channel=PaymentChannel.BANK_TRANSFER,
                            description="SYNTHETIC duplicate candidate",
                            currency="INR",
                        )
                    )
            else:
                db.add(
                    Invoice(
                        id=stable_id(f"{spec['key']}-unmatched-invoice"),
                        business_id=business_id,
                        source_id=invoice_source.id,
                        invoice_no=f"SYN-{spec['key'][-1].upper()}-UNMATCHED",
                        issued_at=date(2025, 12, 12),
                        due_at=date(2026, 1, 11),
                        total_inr=Decimal("27000"),
                        counterparty_id=counterparties[spec["customers"][1]["key"]].id,
                        direction=InvoiceDirection.RECEIVABLE,
                        status=InvoiceStatus.OPEN,
                    )
                )
                db.add(
                    Transaction(
                        id=stable_id(f"{spec['key']}-unmatched-payment"),
                        business_id=business_id,
                        source_id=upi.id,
                        external_ref="SYN-UNMATCHED-PAYMENT",
                        transaction_date=date(2025, 12, 20),
                        amount_inr=Decimal("19000"),
                        direction=TransactionDirection.CREDIT,
                        counterparty_id=counterparties[spec["customers"][0]["key"]].id,
                        payment_channel=PaymentChannel.UPI,
                        description="SYNTHETIC unmatched receipt",
                        currency="INR",
                    )
                )
        if simulate_gateway:
            from app.services.gateway import backfill

            db.flush()
            backfill(db, demo_business_ids, simulate_demo=True)
    return len(config["businesses"])


if __name__ == "__main__":
    import os

    if os.getenv("DEMO_MODE", "0").strip().lower() not in {"1", "true", "yes"}:
        raise SystemExit("Synthetic seeding is disabled; set DEMO_MODE=1 to enable it.")
    print(f"Seeded {seed()} synthetic businesses into configured database ({database_url().split('://', 1)[0]})")
