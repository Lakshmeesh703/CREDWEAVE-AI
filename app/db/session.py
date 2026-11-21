from os import getenv

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool


def database_url() -> str:
    configured = getenv("DATABASE_URL")
    if not configured:
        raise RuntimeError("DATABASE_URL must be set; configure Supabase PostgreSQL before starting the API.")
    return configured


class Base(DeclarativeBase):
    pass


_database_url = database_url()
engine_kwargs = {
    "pool_pre_ping": True,
}
if _database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    if _database_url == "sqlite:///:memory:":
        engine_kwargs["poolclass"] = StaticPool
elif _database_url.startswith("postgresql"):
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 5
    engine_kwargs["connect_args"] = {"prepare_threshold": None}

engine = create_engine(_database_url, **engine_kwargs)


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    if _database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


GATEWAY_TABLES = {"record_provenance", "verification_events"}


def protect_postgres_tables(connection, tables) -> None:
    roles = connection.execute(text(
        "SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated', 'service_role')"
    )).scalars().all()
    grantees = ", ".join(["PUBLIC", *[f'"{role}"' for role in roles]])
    for table in tables:
        table_name = connection.dialect.identifier_preparer.quote(table)
        connection.execute(text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
        connection.execute(text(f"REVOKE ALL PRIVILEGES ON TABLE {table_name} FROM {grantees}"))


def init_db() -> None:
    from app.models import BaseModel  # noqa: F401

    with engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.execute(text("SELECT pg_advisory_xact_lock(308524767)"))
        tables = Base.metadata.sorted_tables
        if connection.dialect.name == "postgresql":
            tables = [table for table in tables if table.name not in GATEWAY_TABLES]
        Base.metadata.create_all(bind=connection, tables=tables)
        inspector = inspect(connection)
        business_columns = {column["name"] for column in inspector.get_columns("businesses")}
        review_columns = {column["name"] for column in inspector.get_columns("reviews")}
        counterparty_columns = {column["name"] for column in inspector.get_columns("counterparties")}
        statements: list[str] = []
        if "source_id" not in counterparty_columns:
            statements.append("ALTER TABLE counterparties ADD COLUMN source_id VARCHAR(36) REFERENCES data_sources(id)")
        if "owner_id" not in business_columns:
            statements.append("ALTER TABLE businesses ADD COLUMN owner_id VARCHAR(36) REFERENCES portal_accounts(id)")
            statements.append("CREATE INDEX ix_businesses_owner_id ON businesses (owner_id)")
        for column in ("source_upload_consent", "passport_sharing_consent"):
            if column not in business_columns:
                statements.append(f"ALTER TABLE businesses ADD COLUMN {column} BOOLEAN")
        if "reviewer_account_id" not in review_columns:
            statements.append("ALTER TABLE reviews ADD COLUMN reviewer_account_id VARCHAR(36) REFERENCES portal_accounts(id)")
        if "checklist_json" not in review_columns:
            statements.append("ALTER TABLE reviews ADD COLUMN checklist_json JSON")
        if "rule_version" not in review_columns:
            statements.append("ALTER TABLE reviews ADD COLUMN rule_version VARCHAR(40)")
        for statement in statements:
            connection.execute(text(statement))

        if connection.dialect.name == "postgresql":
            protect_postgres_tables(connection, [table.name for table in tables])
