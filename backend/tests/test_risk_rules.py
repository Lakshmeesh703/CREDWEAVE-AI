from app.services.risk_rules import evaluate_rules
from app.db.session import Base, SessionLocal, engine
from app.models import Business
from app.models.entities import ConsentStatus
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _financial():
    return {
        "rule_version": "financial-health.v1",
        "monthly": [
            {"inflows_inr": "100000.00", "net_cash_flow_inr": "50000.00"},
            {"inflows_inr": "100000.00", "net_cash_flow_inr": "50000.00"},
        ],
        "metrics": {
            "expense_to_inflow_ratio": {"value": "50.00"},
            "cash_flow_volatility": {"value": "0.00"},
            "negative_months": {"value": 0},
            "supplier_concentration": {"value": "50.00"},
            "monthly_debt_obligations": {"value": "10000.00"},
        },
    }


def _evidence(completeness=100, consistency=100):
    return {
        "evidence_completeness": {"score": completeness, "denominator": 4},
        "evidence_consistency": {"score": consistency, "denominator": 2},
        "verification_status": {"uploaded-only": 0, "cross-source-consistent": 2},
        "assessment_confidence": {"label": "high", "rationale": "coverage"},
        "limitations": ["synthetic"],
    }


def test_identical_finances_have_same_rules_and_no_default_probability():
    complete = evaluate_rules(_financial(), _evidence(100, 100))
    incomplete = evaluate_rules(_financial(), _evidence(50, 50))

    assert complete["risk_indicators"] == incomplete["risk_indicators"]
    assert "probability" not in complete["decision_boundary"].lower()
    assert complete["evidence_quality"]["completeness"]["score"] != incomplete["evidence_quality"]["completeness"]["score"]
    assert complete["assessment_confidence"]["label"] != incomplete["assessment_confidence"]["label"] or complete["assessment_confidence"]["label"] == "high"


def test_elevated_rule_explains_debt_burden():
    financial = _financial()
    financial["metrics"]["monthly_debt_obligations"]["value"] = "50000.00"
    result = evaluate_rules(financial, _evidence())
    debt = next(item for item in result["risk_indicators"] if item["code"] == "debt_to_average_inflow_percent")
    assert debt["status"] == "elevated"
    assert "elevated review threshold" in debt["explanation"]


def test_assessment_endpoint_persists_immutable_snapshot_and_latest_reads_it():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal.begin() as db:
        business = Business(
            name="SYNTHETIC Assessment Shop",
            sector="Retail",
            operating_months=6,
            city="Pune",
            consent_status=ConsentStatus.GRANTED,
        )
        db.add(business)
        db.flush()
        business_id = business.id

    assert client.get(f"/api/businesses/{business_id}/credit-passport").status_code == 404
    created = client.post(f"/api/businesses/{business_id}/assess")
    assert created.status_code == 201
    payload = created.json()
    assert payload["snapshot"]["decision_boundary"].startswith("Rules-only")
    latest = client.get(f"/api/businesses/{business_id}/assessments/latest")
    assert latest.status_code == 200
    assert latest.json()["assessment_id"] == payload["assessment_id"]
    assert latest.json()["snapshot"] == payload["snapshot"]
    passport = client.get(f"/api/businesses/{business_id}/credit-passport")
    assert passport.status_code == 200
    passport_payload = passport.json()
    assert passport_payload["status"] == "Prepared for Human Lender Review"
    assert passport_payload["snapshot"] == payload["snapshot"]
    assert any("never an automatic approval" in item for item in passport_payload["disclosures"])
