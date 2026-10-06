"""Unit and integration tests for manuscript, rights, claims, and submission review."""
from __future__ import annotations

import csv
from pathlib import Path
import pytest


@pytest.fixture
def root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Claim Ledger Verification
# ---------------------------------------------------------------------------

def test_claim_ledger_validity(root_dir: Path) -> None:
    ledger_path = root_dir / "project/claim_ledger.csv"
    assert ledger_path.is_file(), "project/claim_ledger.csv must exist"

    with ledger_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) >= 10, "Claim ledger must contain at least 10 scientific claims"
    required_cols = {
        "claim_id",
        "hypothesis_id",
        "claim_statement",
        "target_population",
        "endpoint_metric",
        "point_estimate",
        "uncertainty_interval",
        "evidence_artifact",
        "inference_scope",
        "status",
    }
    assert required_cols.issubset(set(reader.fieldnames or [])), f"Missing columns in claim ledger: {required_cols - set(reader.fieldnames or [])}"

    valid_statuses = {"supported", "inconclusive", "refuted"}
    for r in rows:
        assert r["status"] in valid_statuses, f"Invalid claim status {r['status']} in {r['claim_id']}"
        assert r["claim_id"].startswith("CLM-"), f"Invalid claim ID format {r['claim_id']}"
        artifact_file = root_dir / r["evidence_artifact"]
        assert artifact_file.is_file(), f"Evidence artifact does not exist: {r['evidence_artifact']}"


# ---------------------------------------------------------------------------
# Model and Data Cards Verification
# ---------------------------------------------------------------------------

def test_model_card_completeness(root_dir: Path) -> None:
    card_path = root_dir / "project/model_card.md"
    assert card_path.is_file(), "project/model_card.md must exist"

    content = card_path.read_text(encoding="utf-8")
    assert "Model Details" in content
    assert "Intended Use" in content
    assert "Out-of-Scope" in content
    assert "4,257 trainable parameters" in content
    assert "Quantitative Performance Summary" in content
    assert "Known Limitations" in content
    assert "0.9444" in content
    assert "+0.2180" in content


def test_data_card_completeness(root_dir: Path) -> None:
    card_path = root_dir / "project/data_card.md"
    assert card_path.is_file(), "project/data_card.md must exist"

    content = card_path.read_text(encoding="utf-8")
    assert "Dataset Motivation" in content
    assert "Dataset Composition" in content
    assert "01646500" in content
    assert "01463500" in content
    assert "01434000" in content
    assert "17 U.S.C. § 105" in content
    assert "Interval-Censored Labeling" in content


# ---------------------------------------------------------------------------
# Venue Requirements and Retraction of Legacy Claims
# ---------------------------------------------------------------------------

def test_venue_requirements_and_retraction(root_dir: Path) -> None:
    venue_path = root_dir / "project/venue_requirements.md"
    assert venue_path.is_file(), "project/venue_requirements.md must exist"

    content = venue_path.read_text(encoding="utf-8")
    assert "Hydrology and Earth System Sciences" in content or "HESS" in content
    assert "Water Resources Research" in content or "WRR" in content
    assert "Transactions on Machine Learning Research" in content or "TMLR" in content
    assert "RETRACTED" in content.upper() or "RETRACTION" in content.upper()

    readme_path = root_dir / "README.md"
    readme_content = readme_path.read_text(encoding="utf-8").lower()
    assert "under peer review at ieee access" not in readme_content, "Unsupported legacy review claim must not appear in README"
    assert "accepted at" not in readme_content


# ---------------------------------------------------------------------------
# Reproducibility, Ethics, and Scientific Review
# ---------------------------------------------------------------------------

def test_reproducibility_guide(root_dir: Path) -> None:
    repro_path = root_dir / "project/reproducibility.md"
    assert repro_path.is_file(), "project/reproducibility.md must exist"

    content = repro_path.read_text(encoding="utf-8")
    assert "Apple M3" in content
    assert "Python 3.12" in content
    assert "run_postprocessing.py" in content
    assert "run_statistical_evaluation.py" in content
    assert "run_hardware_benchmark.py" in content


def test_ethics_and_review(root_dir: Path) -> None:
    ethics_path = root_dir / "project/ethics_limitations.md"
    review_path = root_dir / "project/scientific_review.md"

    assert ethics_path.is_file()
    assert review_path.is_file()

    ethics_text = ethics_path.read_text(encoding="utf-8")
    assert "NOT certified" in ethics_text or "NOT validated" in ethics_text
    assert "False Alarms" in ethics_text
    assert "Missed Warnings" in ethics_text

    review_text = review_path.read_text(encoding="utf-8")
    assert "Scientific Review Checklist" in review_text
    assert "Reviewer Objections" in review_text
    assert "VERIFIED (PASS)" in review_text


# ---------------------------------------------------------------------------
# Manuscript Concordance
# ---------------------------------------------------------------------------

def test_manuscript_metrics_concordance(root_dir: Path) -> None:
    ms_path = root_dir / "project/manuscript.md"
    assert ms_path.is_file(), "project/manuscript.md must exist"

    content = ms_path.read_text(encoding="utf-8")
    assert "0.9444" in content, "Average Precision 0.9444 must be cited in manuscript"
    assert "0.1831" in content, "Brier score 0.1831 must be cited in manuscript"
    assert "+0.2180" in content, "Brier skill score +0.2180 must be cited in manuscript"
    assert "19.12" in content, "Lead time 19.12h must be cited in manuscript"
    assert "0.434" in content, "Single sample latency 0.434ms must be cited in manuscript"
    assert "6,179" in content, "Throughput 6,179 samples/s must be cited in manuscript"
    assert "inconclusive" in content.lower(), "Formal multiplicity outcome inconclusive must be cited in manuscript"
