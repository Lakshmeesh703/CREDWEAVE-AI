import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.synthetic_method_demo import generate_synthetic_entities, run_synthetic_method_demo


def test_synthetic_entity_split_is_reproducible_and_no_evidence_status_is_used():
    first = run_synthetic_method_demo(seed=2026)
    second = run_synthetic_method_demo(seed=2026)

    assert first == second
    assert first["real_world_prediction"] is False
    assert "evidence_verification_status" in first["excluded_from_features"]
    assert "real repayment outcomes" in first["excluded_from_features"]
    assert first["metrics"]["held_out_entities"] == ["synthetic-entity-04"]


def test_generated_labels_and_features_are_synthetic_only():
    data = generate_synthetic_entities(seed=2026)

    assert data["x"].shape == (400, 6)
    assert set(data["y"].tolist()) <= {0, 1}
    assert set(data["entity_ids"].tolist()) == {
        "synthetic-entity-01",
        "synthetic-entity-02",
        "synthetic-entity-03",
        "synthetic-entity-04",
    }


def test_synthetic_metrics_are_labeled_as_not_real_world_risk():
    report = run_synthetic_method_demo(seed=2026)

    assert report["metrics"]["test_rows"] == 100
    assert report["metrics"]["train_rows"] == 300
    assert report["metrics"]["roc_auc"] is None or 0 <= report["metrics"]["roc_auc"] <= 1
    assert "No probability of default" in report["limitations"][3]
