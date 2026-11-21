import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine
from app.main import app
from app.models import Business
from app.models.entities import ConsentStatus
from app.seed import seed, stable_id

client = TestClient(app)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_seed_replaces_demo_profiles_without_deleting_other_businesses():
    seed()
    custom_business = Business(
        id="custom-business",
        name="Preserved Business",
        sector="Other",
        operating_months=12,
        city="Delhi",
        consent_status=ConsentStatus.PENDING,
    )
    with SessionLocal.begin() as db:
        db.add(custom_business)

    assert seed() == 2
    with SessionLocal() as db:
        names = {item.name for item in db.query(Business).all()}
    assert names == {
        "Business A - Sunrise Foods",
        "Business B - Riverbend Repairs",
        "Preserved Business",
    }


def test_seeded_demo_ids_remain_stable():
    seed()
    first_ids = {item["id"] for item in client.get("/api/businesses").json()}

    seed()
    second_ids = {item["id"] for item in client.get("/api/businesses").json()}

    assert first_ids == second_ids == {
        stable_id("business-a"),
        stable_id("business-b"),
    }


def test_demo_load_is_disabled_without_explicit_demo_mode(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "0")

    response = client.post("/api/demo/load")

    assert response.status_code == 403
    assert response.json()["detail"].startswith("Synthetic demo loading is disabled")
