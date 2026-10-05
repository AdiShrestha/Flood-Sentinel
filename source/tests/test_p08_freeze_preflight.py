"""Preflight and schema verification for Work Package P08 freeze."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from factory.engine.io import inventory, read_json
from factory.engine.plan import validate
from source.runners.run_experiment import parse_model_family, TrainPlattCalibrator


@pytest.fixture
def root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def test_research_plan_schema_valid(root_dir: Path) -> None:
    plan_path = root_dir / "project/research_plan.json"
    assert plan_path.is_file(), "Missing project/research_plan.json"
    plan_data = read_json(plan_path)
    # Full factory validator
    validated = validate(root_dir, plan_data)
    assert validated["project_id"] == "flood-sentinel-research-rebuild"
    assert validated["schema_version"] == 3
    assert validated["factory_version"] == "3.3.0"
    assert validated["profile"] == "binary_classification"
    assert validated["intent"] == "fixture"
    assert validated["data_origin"] == "observational"


def test_experiment_registry_coverage(root_dir: Path) -> None:
    plan_data = read_json(root_dir / "project/research_plan.json")
    experiments = plan_data["experiments"]
    assert len(experiments) == 35, f"Expected 35 experiments (7 models x 5 seeds), got {len(experiments)}"

    expected_models = {
        "persistence",
        "ewma_cusum",
        "tabular_ridge",
        "ea_lstm",
        "masked_hydro_score_a",
        "masked_hydro_score_b",
        "causal_forecasting_head",
    }
    expected_seeds = {42, 100, 2026, 31415, 99999}

    found_models = {e["model"] for e in experiments}
    found_seeds = {e["seed"] for e in experiments}
    assert found_models == expected_models
    assert found_seeds == expected_seeds

    for e in experiments:
        assert e["code_paths"] == ["source"]
        assert e["execution_contract"]["runtime_id"] == "python-cpu-v1"
        assert e["execution_contract"]["entrypoint"] == "source/runners/run_experiment.py"
        assert e["threshold"] == 0.5
        assert e["evaluation_splits"] == ["validation", "test"]

        # Parse family
        assert parse_model_family(e["id"]) == e["model"]


def test_comparisons_and_multiplicity(root_dir: Path) -> None:
    plan_data = read_json(root_dir / "project/research_plan.json")
    comparisons = plan_data["comparisons"]
    assert len(comparisons) == 5, f"Expected 5 comparisons, got {len(comparisons)}"

    for c in comparisons:
        assert len(c["pairs"]) == 5, f"Expected 5 seed pairs for {c['id']}, got {len(c['pairs'])}"
        assert c["sampling_unit"] == "seed_fixed_test"
        assert c["inference_scope"] == "fixed_test_corpus"
        assert c["assertion"] == "estimate"
        assert c["alpha"] == 0.05
        assert c["metric"] == "average_precision"

    # Multiplicity family check: single alpha across all confirmatory comparisons
    alphas = {c["alpha"] for c in comparisons}
    assert len(alphas) == 1


def test_claims_bound_correctly(root_dir: Path) -> None:
    plan_data = read_json(root_dir / "project/research_plan.json")
    claims = plan_data["claims"]
    assert len(claims) >= 6, "Expected at least 6 claims (5 comparative + benchmarks)"

    cmp_ids = {c["id"] for c in plan_data["comparisons"]}
    for claim in claims:
        if claim["kind"] == "comparative":
            assert claim["comparison_id"] in cmp_ids
            assert claim["population"] == "fixed_test_corpus"
            assert claim["inference_scope"] == "fixed_test_corpus"


def test_frozen_paths_inventory_clean(root_dir: Path) -> None:
    plan_data = read_json(root_dir / "project/research_plan.json")
    inv = inventory(root_dir, plan_data["frozen_paths"], reject_dangerous_ext=True)
    assert len(inv) > 0
    for path in inv.keys():
        assert not path.endswith(".pyc"), f"Found .pyc in frozen inventory: {path}"
        assert not path.endswith(".so"), f"Found .so in frozen inventory: {path}"


def test_platt_calibrator_properties() -> None:
    scores = [-2.0, -1.0, 1.0, 2.0]
    labels = [0, 0, 1, 1]
    cal = TrainPlattCalibrator().fit(scores, labels)
    assert cal.w >= 0.01

    probs = cal.predict(scores)
    assert len(probs) == 4
    assert all(0.0 < p < 1.0 for p in probs)
    # Check monotonicity
    assert probs[0] < probs[1] < probs[2] < probs[3]
