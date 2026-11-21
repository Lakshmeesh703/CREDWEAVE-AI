"""Promote the first admin from an existing, verified portal account."""
import argparse
from uuid import UUID

from sqlalchemy import select, text

from app.db.session import SessionLocal
from app.models.entities import Business, PortalAccount


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("account_id", type=UUID, help="Verified Supabase user ID after first portal login")
    args = parser.parse_args()
    with SessionLocal.begin() as db:
        if db.bind.dialect.name != "postgresql":
            parser.error("Use the configured portal PostgreSQL database.")
        db.execute(text("SELECT pg_advisory_xact_lock(308524766)"))
        if db.scalar(select(PortalAccount.id).where(PortalAccount.role == "admin").limit(1)):
            parser.error("The first administrator already exists.")
        account = db.scalar(select(PortalAccount).where(PortalAccount.id == str(args.account_id)).with_for_update())
        if account is None or account.role != "owner":
            parser.error("Sign in first with a dedicated, verified account.")
        if db.scalar(select(Business.id).where(Business.owner_id == account.id).limit(1)):
            parser.error("Use a dedicated account with no registered businesses.")
        account.role = "admin"
    print("Administrator role assigned.")


if __name__ == "__main__":
    main()
