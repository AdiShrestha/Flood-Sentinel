"""Skip legacy tests whose private, untracked artifacts are absent.

The P01-P14 legacy pipeline tests read cohort files, provider captures and
release artifacts under ``data/``, ``project/`` and a handoff archive. Those
paths are deliberately excluded from the public repository. In a public
checkout the dependent tests are skipped with the exact missing path named in
the skip reason; when the artifacts are present locally the tests run
unchanged. The mapping is explicit so that no other failure is ever hidden.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_COHORT = ("data/cohort.csv", "data/source_records.csv")
_PROVIDER_MANIFEST = ("data/manifests/provider_manifest.jsonl",)
_EVENTS = ("data/event_intervals.csv",)

# test module -> {test name or "*" for every test in the module: required paths}
PRIVATE_ARTIFACTS: dict[str, dict[str, tuple[str, ...]]] = {
    "test_p01_source_feasibility.py": {
        "test_manifest_existence_and_nonempty": _PROVIDER_MANIFEST,
        "test_manifest_schema_and_payload_integrity": _PROVIDER_MANIFEST,
        "test_noaa_nwps_flood_stage_structure": _PROVIDER_MANIFEST,
        "test_usgs_nwis_iv_structure": _PROVIDER_MANIFEST,
    },
    "test_p02_acquisition_decode.py": {
        "test_usgs_iv_decoder_sample": ("data/raw/samples/usgs_nwis_01646500_iv.json",),
        "test_noaa_nwps_decoder_sample": ("data/raw/samples/noaa_nwps_01646500_nwps.json",),
        "test_daymet_decoder_sample": ("data/raw/samples/nasa_daymet_01646500_daymet.json",),
        "test_source_records_csv_schema_and_integrity": ("data/source_records.csv",),
    },
    "test_p03_event_definitions.py": {
        "test_rejection_of_fabricated_noon_onsets": _EVENTS,
        "test_catalog_parquet_and_csv_consistency": _EVENTS + ("data/event_intervals.parquet",),
    },
    "test_p04_split_cohort.py": {
        name: _COHORT
        for name in (
            "test_cohort_file_exists_and_schema_valid",
            "test_zero_group_leakage_across_splits",
            "test_zero_source_record_leakage_across_splits",
            "test_all_source_ids_exist_in_source_records",
            "test_minimum_class_counts_in_all_splits",
            "test_test_split_independent_group_floor",
            "test_strict_causal_availability_filtering",
            "test_tamper_detection_in_cohort",
        )
    },
    "test_p05_domain_adapters.py": {
        "test_ancestry_adapter_authentic_cohort": _COHORT,
        "test_ancestry_adapter_duplicate_source_rejection": _COHORT,
        "test_ancestry_adapter_missing_source_rejection": _COHORT,
        "test_mutation_04_source_duplication": _COHORT,
    },
    "test_p06_pipeline_objective.py": {
        "test_legacy_dataset_without_release_evidence_is_rejected": _COHORT,
        "test_unverified_development_batch_cannot_enter_training": _COHORT,
    },
    "test_p10_postprocessing.py": {
        "test_evaluate_warning_lead_times_on_authentic_intervals": _EVENTS,
        "test_evaluate_warning_lead_times_empty_predictions": _EVENTS,
        "test_postprocessing_runner_integration": _COHORT + _EVENTS + ("project/development",),
        "test_postprocessing_summary_files_exist_and_valid": ("project/postprocessing_summary.json",),
    },
    "test_p11_statistical_analysis.py": {
        "test_run_statistical_evaluation_e2e": _COHORT + ("project/development",),
    },
    "test_p12_hardware_reproducibility.py": {
        "test_traceability_figures_and_statistical_summary": ("project/figures_data.json",),
        "test_hardware_metrics_artifacts_exist_and_valid": ("project/hardware_metrics.json",),
    },
    "test_p13_manuscript_rights.py": {
        "test_claim_ledger_validity": ("project/claim_ledger.csv",),
        "test_model_card_completeness": ("project/model_card.md",),
        "test_data_card_completeness": ("project/data_card.md",),
        "test_venue_requirements_and_retraction": ("project/venue_requirements.md",),
        "test_reproducibility_guide": ("project/reproducibility.md",),
        "test_ethics_and_review": ("project/ethics_limitations.md",),
        "test_manuscript_metrics_concordance": ("project/manuscript.md",),
    },
    "test_p14_release_handoff.py": {"*": ("project/release_manifest.json", "handoff_epoch0007_verified.zip")},
    "test_revalidation.py": {
        "test_forensic_comparison_rejects_equal_length_dates_in_different_order": (
            "project/audit/tools/inspect_legacy_evidence.py",
        ),
    },
}


def _required_paths(item: pytest.Item) -> tuple[str, ...]:
    by_test = PRIVATE_ARTIFACTS.get(item.path.name)
    if not by_test:
        return ()
    name = item.originalname if hasattr(item, "originalname") else item.name
    return by_test.get(name, by_test.get("*", ()))


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        missing = [p for p in _required_paths(item) if not (REPO_ROOT / p).exists()]
        if missing:
            item.add_marker(
                pytest.mark.skip(
                    reason="requires untracked private artifact(s): " + ", ".join(missing)
                )
            )
