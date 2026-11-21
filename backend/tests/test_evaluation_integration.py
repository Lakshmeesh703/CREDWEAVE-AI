import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine
from app.main import app
from app.seed import seed, stable_id

client = TestClient(app)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_seeded_business_a_and_b_follow_full_api_journey():
    assert seed() == 2

    businesses = client.get("/api/businesses")
    assert businesses.status_code == 200
    listed = {item["name"]: item for item in businesses.json()}
    assert "Business A - Sunrise Foods" in listed
    assert "Business B - Riverbend Repairs" in listed

    for key in ("business-a", "business-b"):
        business_id = stable_id(key)
        assert client.get(f"/api/businesses/{business_id}").status_code == 200

        evidence = client.get(f"/api/businesses/{business_id}/evidence-dna")
        graph = client.get(f"/api/businesses/{business_id}/trust-graph")
        finance = client.get(f"/api/businesses/{business_id}/financial-summary")
        assessment = client.post(f"/api/businesses/{business_id}/assess")
        passport = client.get(f"/api/businesses/{business_id}/credit-passport")
        review = client.post(
            f"/api/businesses/{business_id}/reviews",
            json={
                "reviewer_name_or_alias": "synthetic-evaluation-reviewer",
                "status": "reviewed",
                "reason": "Synthetic end-to-end evaluation review.",
                "checklist": {"human_decision_pending": True},
            },
        )

        assert evidence.status_code == 200
        assert graph.status_code == 200
        assert finance.status_code == 200
        assert assessment.status_code == 201
        assert passport.status_code == 200
        assert review.status_code == 201

        passport_payload = passport.json()
        assert passport_payload["status"] == "Prepared for Human Lender Review"
        assert passport_payload["snapshot"]["business"]["name"]
        assert passport_payload["snapshot"]["evidence_dna"]
        assert passport_payload["snapshot"]["trust_graph"]
        assert passport_payload["snapshot"]["financial_summary"]
        assert passport_payload["snapshot"]["cashflow_twin"]
        assert passport_payload["snapshot"]["loan_options"]


def test_seeded_profiles_have_planted_contrast_labels():
    seed()
    business_a = stable_id("business-a")
    business_b = stable_id("business-b")

    evidence_a = client.get(f"/api/businesses/{business_a}/evidence-dna").json()
    evidence_b = client.get(f"/api/businesses/{business_b}/evidence-dna").json()

    graph_a = client.get(f"/api/businesses/{business_a}/trust-graph").json()
    graph_b = client.get(f"/api/businesses/{business_b}/trust-graph").json()

    assert evidence_a["evidence_completeness"]["score"] == evidence_b["evidence_completeness"]["score"]
    assert evidence_a["evidence_consistency"]["score"] > evidence_b["evidence_consistency"]["score"]

    a_codes = {finding["code"] for finding in evidence_a["findings"]}
    b_codes = {finding["code"] for finding in evidence_b["findings"]}
    graph_a_codes = {finding["code"] for finding in graph_a["anomalies"]}
    graph_b_codes = {finding["code"] for finding in graph_b["anomalies"]}

    assert "DUPLICATE_RECORD_CANDIDATE" in a_codes
    assert "UNMATCHED_INVOICE" in b_codes
    assert "UNMATCHED_PAYMENT" in b_codes
    assert "DUPLICATE_RECORD_CANDIDATE" not in b_codes
    assert "UNMATCHED_INVOICE" not in a_codes
    assert graph_a_codes or graph_b_codes


def test_documented_demo_figures_match_seeded_api_responses():
    seed()
    business_a = stable_id("business-a")
    business_b = stable_id("business-b")

    evidence_a = client.get(f"/api/businesses/{business_a}/evidence-dna").json()
    evidence_b = client.get(f"/api/businesses/{business_b}/evidence-dna").json()
    finance_a = client.get(f"/api/businesses/{business_a}/financial-summary").json()
    finance_b = client.get(f"/api/businesses/{business_b}/financial-summary").json()
    graph_b = client.get(f"/api/businesses/{business_b}/trust-graph").json()

    assert evidence_a["claim_to_evidence"]["reported_amount_inr"] == "100000"
    assert evidence_b["claim_to_evidence"]["reported_amount_inr"] == "100000"
    assert evidence_a["evidence_completeness"]["score"] == 100
    assert evidence_b["evidence_completeness"]["score"] == 100
    assert evidence_a["evidence_consistency"]["score"] == 90
    assert evidence_b["evidence_consistency"]["score"] == 43
    assert finance_a["metrics"]["total_inflows"]["value"] == "613000.00"
    assert finance_a["metrics"]["total_outflows"]["value"] == "228000.00"
    assert finance_a["metrics"]["net_operating_cash_flow"]["value"] == "385000.00"
    assert finance_a["metrics"]["monthly_debt_obligations"]["value"] == "8500.00"
    assert finance_b["metrics"]["total_inflows"]["value"] == "571000.00"
    assert finance_b["metrics"]["total_outflows"]["value"] == "228000.00"
    assert finance_b["metrics"]["net_operating_cash_flow"]["value"] == "343000.00"
    assert finance_b["metrics"]["monthly_debt_obligations"]["value"] == "16500.00"
    assert graph_b["metrics"]["anomaly_count"] == 8
    assert {item["code"] for item in graph_b["anomalies"]} == {
        "UNMATCHED_INVOICE",
        "UNMATCHED_PAYMENT",
    }

    sales_decline = client.post(
        f"/api/businesses/{business_a}/stress-tests",
        json={
            "revenue_shock_pct": -20,
            "expense_shock_pct": 0,
            "payment_delay_days": 0,
            "duration_months": 6,
            "selected_loan_emi": "0",
            "seasonal_weaker_months": 0,
        },
    ).json()
    combined_crisis = client.post(
        f"/api/businesses/{business_a}/stress-tests",
        json={
            "revenue_shock_pct": -20,
            "expense_shock_pct": 15,
            "payment_delay_days": 45,
            "duration_months": 6,
            "selected_loan_emi": "18336",
            "seasonal_weaker_months": 2,
        },
    ).json()
    assert sales_decline["metrics"]["minimum_net_cash_after_emi_inr"] == "34800.00"
    assert combined_crisis["metrics"]["minimum_net_cash_after_emi_inr"] == "-66636.00"
    assert combined_crisis["metrics"]["receipts_delayed_beyond_horizon_inr"] == "156800.00"

    loan_options = client.post(
        f"/api/businesses/{business_a}/loan-options",
        json={
            "principal_inr": "200000",
            "annual_interest_rate_pct": 18,
            "tenure_months": [6, 12, 18, 24],
            "origination_fee_inr": "0",
        },
    ).json()
    assert [item["emi_inr"] for item in loan_options["options"]] == [
        "35105.04",
        "18336.00",
        "12761.16",
        "9984.82",
    ]
