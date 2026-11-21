import os

import pytest

# Tests rebuild the schema and must never inherit a live database URL.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"


@pytest.fixture(autouse=True)
def isolated_demo_for_existing_regression_tests(monkeypatch, request):
    from app.main import app

    monkeypatch.setattr(app.state, "synthetic_demo", request.module.__name__ != "test_portal", raising=False)
