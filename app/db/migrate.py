"""Apply pending versions after the existing portal schema is initialized."""

from sqlalchemy import text

from app.db.migrations import v0001_verified_evidence
from app.db.session import engine, protect_postgres_tables

MIGRATIONS = (v0001_verified_evidence,)


def main() -> None:
    if engine.dialect.name != "postgresql":
        raise SystemExit("The migration command requires the configured PostgreSQL database.")
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(308524767)"))
        connection.execute(text(
            "CREATE TABLE IF NOT EXISTS credweave_schema_migrations "
            "(version VARCHAR(80) PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        ))
        protect_postgres_tables(connection, ["credweave_schema_migrations"])
        applied = set(connection.execute(text("SELECT version FROM credweave_schema_migrations")).scalars())
        for migration in MIGRATIONS:
            if migration.VERSION not in applied:
                migration.apply(connection)
                connection.execute(text("INSERT INTO credweave_schema_migrations (version) VALUES (:version)"),
                                   {"version": migration.VERSION})
    print("CredWeave migrations are up to date.")


if __name__ == "__main__":
    main()
