from sqlalchemy import inspect

from app.db.session import Base
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
from app.schemas.contracts import BusinessCreate
from app.models.entities import ConsentStatus


def test_all_prompt02_tables_are_registered() -> None:
    expected = {
        "businesses",
        "data_sources",
        "transactions",
        "invoices",
        "payment_links",
        "counterparties",
        "obligations",
        "assessments",
        "reviews",
    }

    assert expected.issubset(Base.metadata.tables)


def test_money_columns_use_numeric() -> None:
    for model, column_name in (
        (Transaction, "amount_inr"),
        (Invoice, "total_inr"),
        (PaymentLink, "linked_amount_inr"),
        (Obligation, "monthly_payment_inr"),
    ):
        column = inspect(model).columns[column_name]
        assert column.type.precision == 14
        assert column.type.scale == 2


def test_business_contract_validates_enum_and_required_fields() -> None:
    business = BusinessCreate(
        name="Synthetic Shop",
        sector="Retail",
        operating_months=12,
        city="Pune",
        consent_status=ConsentStatus.GRANTED,
    )

    assert business.consent_status == "granted"
