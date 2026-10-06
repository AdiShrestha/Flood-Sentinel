"""Unit and integration tests for release packaging, handoff verification, and offline reproduction."""
from __future__ import annotations

import json
from pathlib import Path
import pytest
import zipfile

from flood_sentinel.release import (
    generate_release_manifest,
    verify_handoff_archive,
    verify_release_manifest,
    verify_standalone_reproduction,
)
from source.runners.verify_standalone_bundle import (
    run_standalone_bundle_verification,
)


@pytest.fixture
def root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Release Manifest Tests
# ---------------------------------------------------------------------------

def test_release_manifest_schema_and_completeness(root_dir: Path) -> None:
    manifest_path = root_dir / "project/release_manifest.json"
    assert manifest_path.is_file(), "Missing project/release_manifest.json"

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["manifest_version"] == "1.0.0"
    assert data["project_id"] == "flood-sentinel-research-rebuild"
    assert "generated_at_utc" in data
    assert "manifest_digest" in data
    assert data["total_files"] >= 90
    assert data["total_size_bytes"] > 0

    files = data["files"]
    categories = {meta["category"] for meta in files.values()}
    assert "source" in categories
    assert "runners" in categories
    assert "tests" in categories
    assert "data" in categories
    assert "configuration" in categories
    assert "documentation" in categories
    assert "evaluation_artifacts" in categories


def test_release_manifest_hash_integrity(root_dir: Path) -> None:
    manifest_path = root_dir / "project/release_manifest.json"
    assert manifest_path.is_file()

    res = verify_release_manifest(root_dir, manifest_path)
    assert res["status"] == "PASS"
    assert len(res["missing_files"]) == 0
    assert len(res["hash_mismatches"]) == 0
    assert res["verified_files"] == res["total_declared_files"]


def test_manuscript_and_cards_indexed_in_manifest(root_dir: Path) -> None:
    manifest_path = root_dir / "project/release_manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = set(data["files"].keys())

    required_docs = [
        "project/manuscript.md",
        "project/model_card.md",
        "project/data_card.md",
        "project/claim_ledger.csv",
        "project/venue_requirements.md",
        "project/reproducibility.md",
        "project/data_rights.md",
        "project/ethics_limitations.md",
        "project/scientific_review.md",
        "project/results.md",
        "project/statistical_report.md",
    ]
    for doc in required_docs:
        assert doc in files, f"Document '{doc}' not indexed in release manifest"


# ---------------------------------------------------------------------------
# Handoff Archive Tests
# ---------------------------------------------------------------------------

def test_handoff_archive_structure_and_receipts(root_dir: Path) -> None:
    archive_path = root_dir / "handoff_epoch0007_verified.zip"
    assert archive_path.is_file(), "Missing handoff_epoch0007_verified.zip"

    res = verify_handoff_archive(archive_path)
    assert res["status"] == "PASS"
    assert res["zip_test_passed"] is True
    assert res["execution_receipts_found"] == 36
    assert res["prediction_files_found"] == 36
    assert res["declared_files_in_manifest"] > 100


def test_handoff_manifest_embedded_integrity(root_dir: Path) -> None:
    archive_path = root_dir / "handoff_epoch0007_verified.zip"
    with zipfile.ZipFile(archive_path, "r") as zf:
        manifest_raw = zf.read("handoff_manifest.json").decode("utf-8")
        manifest_data = json.loads(manifest_raw)
        assert manifest_data["archive_type"] == "verified_research_handoff"
        assert manifest_data["epoch"] == "epoch_0007"
        assert "archive_digest" in manifest_data
        assert manifest_data["n_files"] > 100


# ---------------------------------------------------------------------------
# Standalone Reproduction Tests
# ---------------------------------------------------------------------------

def test_offline_reproduction_checks(root_dir: Path) -> None:
    res = verify_standalone_reproduction(root_dir)
    assert res["status"] == "PASS"
    assert res["offline_reproducible"] is True
    assert res["normalizer_fitted"] is True
    assert res["n_test_samples"] == 5
    assert 0.0 <= res["sample_forward_score"] <= 1.0


def test_standalone_bundle_verification_runner_e2e(root_dir: Path) -> None:
    res = run_standalone_bundle_verification(root_dir, generate_if_missing=False)
    assert res["status"] == "PASS"
    assert res["manifest_verification"]["status"] == "PASS"
    assert res["handoff_verification"]["status"] == "PASS"
    assert res["standalone_reproduction"]["status"] == "PASS"
