"""Reset only the two fixed synthetic demo businesses."""

import argparse
from os import getenv


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replace the two fixed CREDWEAVE synthetic demo businesses."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="confirm replacing the two seeded demo businesses",
    )
    args = parser.parse_args()

    if not args.yes:
        parser.error("Pass --yes after confirming the configured database target.")
    if getenv("DEMO_MODE", "0").strip().lower() not in {"1", "true", "yes"}:
        parser.error("Set DEMO_MODE=1 before resetting the synthetic demo.")

    from sqlalchemy.engine import make_url

    from app.db.session import database_url
    from app.seed import seed

    target = make_url(database_url())
    if target.get_backend_name() != "postgresql":
        parser.error("Demo reset requires the configured PostgreSQL database; local databases are not supported.")

    print(f"Target database: {target.host or 'unknown-host'}/{target.database or 'unknown-database'}")
    print("Scope: Business A - Sunrise Foods and Business B - Riverbend Repairs only.")
    print("Other business records are left unchanged.")
    print(f"Reset complete; seeded {seed()} synthetic businesses.")


if __name__ == "__main__":
    main()
