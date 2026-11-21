from fastapi.testclient import TestClient

from app.main import app
from app.seed import seed, stable_id


def test_only_explicit_mock_verification_gets_the_simulated_status():
    with TestClient(app) as client:
        business = stable_id("business-a")
        path = f"/api/businesses/{business}/verified-evidence"
        seed(simulate_gateway=True)
        page = client.get(path).json()
        assert page["counts"]["SIMULATED_SOURCE_VERIFIED"] > 0
        assert "SOURCE_VERIFIED" not in page["counts"]
        demo = next(item for item in page["items"] if item["result"]["status"] == "SIMULATED_SOURCE_VERIFIED")
        assert demo["source_type"] == "SIMULATED" and demo["file_sha256"] is None
        assert "No bank" in demo["result"]["limitations"][0]
        seed(simulate_gateway=True)
        assert client.get(path).json()["counts"] == page["counts"]
