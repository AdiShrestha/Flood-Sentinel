"""Replication Packaging and Reproducibility Guide Engine (C09-02).

Generates top-level REPRODUCIBILITY.md and project/chunks/chunk09/replication_manifest.json,
providing a complete, leak-free, step-by-step external replication protocol for Flood Sentinel.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import (
    REPO_ROOT,
    CHUNK09_DIR,
    CHUNK09_DATA_DIR
)
from source.utils.logging_config import get_logger

logger = get_logger("package_replication")


def generate_replication_package() -> Dict[str, Any]:
    """Generate replication guide and manifest."""
    logger.info("Generating Flood Sentinel Replication Package (C09-02)...")

    # Load final results manifest for dynamic value insertion (C10-00 structural fix)
    manifest_json_path = REPO_ROOT / "project" / "chunks" / "chunk10" / "final_results_manifest.json"
    if manifest_json_path.exists():
        with open(manifest_json_path, "r", encoding="utf-8") as _mf:
            final_results = json.load(_mf)
    else:
        # Fallback: build it on-the-fly from source artifacts
        from source.release.build_final_results_manifest import build_manifest
        final_results = build_manifest(manifest_json_path)

    # 1. Define Pipeline Stages for Manifest
    stages = [
        {
            "stage_id": "stage_01_acquisition",
            "chunk": "chunk02",
            "name": "Earth Observation & Hydrometric Data Acquisition",
            "scripts": [
                "source/acquisition/verify_full_panel.py",
                "source/acquisition/verify_usgs_full.py",
                "source/acquisition/verify_gridmet_full.py",
                "source/acquisition/verify_snodas_full.py",
                "source/acquisition/verify_attributes_full.py",
                "source/acquisition/verify_thresholds_full.py",
                "source/acquisition/verify_nwm_retro_full.py",
                "source/acquisition/verify_events_full.py"
            ],
            "primary_outputs": [
                "project/chunks/chunk02/data/usgs_streamflow_full.parquet",
                "project/chunks/chunk02/data/gridmet_forcing_full.parquet",
                "project/chunks/chunk02/data/snodas_swe_full.parquet",
                "project/chunks/chunk02/data/static_attributes_full.parquet",
                "project/chunks/chunk02/data/nwps_thresholds_full.parquet",
                "project/chunks/chunk02/data/nwm_retrospective_full.parquet",
                "project/chunks/chunk02/data/flood_events_full.parquet"
            ]
        },
        {
            "stage_id": "stage_02_features",
            "chunk": "chunk03",
            "name": "Feature Engineering, Temporal Windowing & Latency Registry",
            "scripts": [
                "source/feature/verify_latency_registry.py"
            ],
            "primary_outputs": [
                "source/feature/latency_registry.json"
            ]
        },
        {
            "stage_id": "stage_03_encoder_pretrain",
            "chunk": "chunk04",
            "name": "C-ENCODER Causal Representation Pretraining",
            "scripts": [
                "source/model/c_encoder.py",
                "source/model/pretrain_dataset.py",
                "source/model/pretrain_encoder.py",
                "source/model/verify_encoder_convergence.py"
            ],
            "primary_outputs": [
                "project/chunks/chunk04/c_encoder_pretrained.pt",
                "project/chunks/chunk04/pretrain_history.json"
            ]
        },
        {
            "stage_id": "stage_04_precursor_scoring",
            "chunk": "chunk05",
            "name": "Precursor Anomaly Score Extraction & Calibration",
            "scripts": [
                "source/scorer/calibration.py",
                "source/scorer/score_a.py",
                "source/scorer/score_b.py",
                "source/scorer/score_c.py",
                "source/scorer/verify_calibration_isolation.py"
            ],
            "primary_outputs": [
                "project/chunks/chunk05/calibration_params.json",
                "project/chunks/chunk05/data/score_a_val.parquet",
                "project/chunks/chunk05/data/score_a_test.parquet",
                "project/chunks/chunk05/data/score_b_val.parquet",
                "project/chunks/chunk05/data/score_b_test.parquet",
                "project/chunks/chunk05/data/score_c_val.parquet",
                "project/chunks/chunk05/data/score_c_test.parquet"
            ]
        },
        {
            "stage_id": "stage_05_baselines",
            "chunk": "chunk06",
            "name": "Comparative Baseline Benchmark Suite",
            "scripts": [
                "source/baseline/baseline_op.py",
                "source/baseline/baseline_stat.py",
                "source/baseline/baseline_learn.py",
                "source/baseline/ea_lstm.py",
                "source/baseline/baseline_sup.py",
                "source/baseline/label_budget_sweep.py",
                "source/baseline/threshold_registry.py",
                "source/baseline/verify_all_baselines.py"
            ],
            "primary_outputs": [
                "project/chunks/chunk06/data/baseline_nwm_retro_test.parquet",
                "project/chunks/chunk06/data/baseline_stat_test.parquet",
                "project/chunks/chunk06/data/baseline_learn_test.parquet",
                "project/chunks/chunk06/data/baseline_sup_test.parquet",
                "project/chunks/chunk06/data/label_budget_sweep_results.parquet",
                "project/chunks/chunk06/threshold_registry.json"
            ]
        },
        {
            "stage_id": "stage_06_statistical_evaluation",
            "chunk": "chunk07",
            "name": "Hypothesis Testing & Survival Lead-Time Analysis",
            "scripts": [
                "source/stats/collapse_events.py",
                "source/stats/eval_discrimination.py",
                "source/stats/eval_lead_time_survival.py",
                "source/stats/eval_sample_adequacy.py",
                "source/stats/verify_chunk07_reality_gate.py"
            ],
            "primary_outputs": [
                "project/chunks/chunk07/data/discrimination_table.parquet",
                "project/chunks/chunk07/data/survival_curves.parquet",
                "project/chunks/chunk07/discrimination_results.json",
                "project/chunks/chunk07/lead_time_survival_results.json",
                "project/chunks/chunk07/statistical_evaluation_master_report.md"
            ]
        },
        {
            "stage_id": "stage_07_ablations",
            "chunk": "chunk08",
            "name": "Ablation Studies & Sensitivity Sweeps",
            "scripts": [
                "source/ablation/sensor_ablation.py",
                "source/ablation/architecture_ablation.py",
                "source/ablation/causal_masking_ablation.py",
                "source/ablation/hyperparameter_sensitivity.py",
                "source/ablation/audit_title_claims.py",
                "source/ablation/verify_chunk08_reality_gate.py"
            ],
            "primary_outputs": [
                "project/chunks/chunk08/data/sensor_ablation_results.parquet",
                "project/chunks/chunk08/data/architecture_ablation_results.parquet",
                "project/chunks/chunk08/data/causal_masking_ablation_results.parquet",
                "project/chunks/chunk08/data/hyperparameter_sensitivity_results.parquet",
                "project/chunks/chunk08/ablation_master_report.md"
            ]
        },
        {
            "stage_id": "stage_08_release",
            "chunk": "chunk09",
            "name": "Release Packaging & Consistency Auditing",
            "scripts": [
                "source/release/verify_key_facts.py",
                "source/release/package_replication.py"
            ],
            "primary_outputs": [
                "REPRODUCIBILITY.md",
                "project/key_facts.md"
            ]
        }
    ]

    # Save Replication Manifest JSON
    CHUNK09_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = CHUNK09_DIR / "replication_manifest.json"
    manifest_data = {
        "project": "flood-sentinel",
        "title": "Self-Supervised Multi-Sensor Neural Representations for Hydrological Flood Precursor Detection Across CONUS Basins",
        "total_stages": len(stages),
        "stages": stages
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    logger.info(f"Replication manifest written to {manifest_path}.")

    # 2. Author REPRODUCIBILITY.md
    reproducibility_lines = [
        "# Reproducibility Guide — Flood Sentinel",
        "",
        "This guide provides complete, step-by-step instructions to reproduce all empirical findings, neural models, baseline comparators, statistical hypothesis tests, and ablation studies reported in:",
        "",
        "> **\"Self-Supervised Multi-Sensor Neural Representations for Hydrological Flood Precursor Detection Across CONUS Basins\"**",
        "",
        "---",
        "",
        "## 1. System Requirements & Environment Setup",
        "",
        "### Hardware Requirements",
        "- **Processor:** Standard x86_64 or Apple Silicon CPU (Multi-core recommended, $\\ge 4$ cores).",
        "- **Memory:** Minimum 8 GB RAM (16 GB recommended).",
        "- **Storage:** $\\approx 2\\text{ GB}$ free disk space for raw data cache, feature arrays, and checkpoints.",
        "- **Compute Budget:** ~2.0 hours total execution time on standard CPU hardware (no GPU required).",
        "",
        "### Software Requirements",
        "- **Operating System:** Linux (Ubuntu 20.04+), macOS (12.0+), or Windows (WSL2).",
        "- **Python:** Python 3.10, 3.11, or 3.12.",
        "",
        "### Environment Installation",
        "Clone the repository and install the exact pinned scientific dependencies:",
        "",
        "```bash",
        "# Clone repository",
        "git clone https://github.com/flood-sentinel/flood-sentinel.git",
        "cd flood-sentinel",
        "",
        "# Create and activate virtual environment",
        "python3 -m venv .venv",
        "source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate",
        "",
        "# Install pinned dependencies",
        "pip install --upgrade pip",
        "pip install -r requirements.txt",
        "```",
        "",
        "---",
        "",
        "## 2. End-to-End Sequential Replication Pipeline",
        "",
        "Execute the following stages in sequence from the repository root:",
        "",
        "### Stage 1: Earth Observation & Hydrometric Data Acquisition (Chunk 02)",
        "Acquires 34-year records (1990–2023) for all 54 CONUS panel streamgages across USGS streamflow, gridMET meteorology, SNODAS snowpack, GAGES-II/NID static attributes, and NOAA NWPS flood stages:",
        "```bash",
        "python3 source/acquisition/verify_full_panel.py",
        "python3 source/acquisition/verify_usgs_full.py",
        "python3 source/acquisition/verify_gridmet_full.py",
        "python3 source/acquisition/verify_snodas_full.py",
        "python3 source/acquisition/verify_attributes_full.py",
        "python3 source/acquisition/verify_thresholds_full.py",
        "python3 source/acquisition/verify_nwm_retro_full.py",
        "python3 source/acquisition/verify_events_full.py",
        "python3 source/gate/run_reality_gate.py --manifest-dir project/chunks/chunk02/manifests/",
        "```",
        "",
        "### Stage 2: Feature Engineering & Latency Registry (Chunk 03)",
        "Validates physical sensor publication latencies and temporal feature windowing:",
        "```bash",
        "python3 source/feature/verify_latency_registry.py",
        "```",
        "",
        "### Stage 3: C-ENCODER Self-Supervised Pretraining (Chunk 04)",
        "Pretrains the 146,950-parameter hybrid Dilated Causal TCN + Transformer on 9,760 unlabeled multi-sensor temporal windows ($r = 0.15$ dynamic masking):",
        "```bash",
        "python3 source/model/c_encoder.py",
        "python3 source/model/pretrain_encoder.py --epochs 10 --batch-size 64",
        "python3 source/model/verify_encoder_convergence.py",
        "```",
        "",
        "### Stage 4: Calibration & Precursor Anomaly Scoring (Chunk 05)",
        "Calibrates pre-evaluation gauge statistics and extracts precursor score streams (Score-A reconstruction, Score-B latent distance, Score-C latent transition):",
        "```bash",
        "python3 source/scorer/calibration.py",
        "python3 source/scorer/score_a.py",
        "python3 source/scorer/score_b.py",
        "python3 source/scorer/score_c.py",
        "python3 source/scorer/verify_calibration_isolation.py",
        "```",
        "",
        "### Stage 5: Comparative Baseline Benchmark Suite (Chunk 06)",
        "Trains and evaluates all physical, statistical, unsupervised ML, and supervised deep learning comparators, including the 26-condition EA-LSTM label sweep:",
        "```bash",
        "python3 source/baseline/baseline_op.py",
        "python3 source/baseline/baseline_stat.py",
        "python3 source/baseline/baseline_learn.py",
        "python3 source/baseline/baseline_sup.py",
        "python3 source/baseline/label_budget_sweep.py",
        "python3 source/baseline/threshold_registry.py",
        "python3 source/baseline/verify_all_baselines.py",
        "```",
        "",
        "### Stage 6: Statistical Evaluation & Hypothesis Testing (Chunk 07)",
        "Executes window-event collapse, discrimination batteries with Wilcoxon FDR tests, Kaplan-Meier lead-time survival analysis, and sample adequacy verification:",
        "```bash",
        "python3 source/stats/collapse_events.py",
        "python3 source/stats/eval_discrimination.py",
        "python3 source/stats/eval_lead_time_survival.py",
        "python3 source/stats/eval_sample_adequacy.py",
        "python3 source/stats/verify_chunk07_reality_gate.py",
        "```",
        "",
        "### Stage 7: Ablation Studies & Sensitivity Grids (Chunk 08)",
        "Runs physical sensor holdout, neural architecture comparisons, causal attention validation, hyperparameter sweeps, and title claim audits:",
        "```bash",
        "python3 source/ablation/sensor_ablation.py",
        "python3 source/ablation/architecture_ablation.py",
        "python3 source/ablation/causal_masking_ablation.py",
        "python3 source/ablation/hyperparameter_sensitivity.py",
        "python3 source/ablation/audit_title_claims.py",
        "python3 source/ablation/verify_chunk08_reality_gate.py",
        "```",
        "",
        "### Stage 8: Release Packaging & Integrity Certification (Chunk 09)",
        "Verifies machine-readable key-fact consistency and release integrity:",
        "```bash",
        "python3 source/release/verify_key_facts.py",
        "python3 source/release/package_replication.py",
        "```",
        "",
        "---",
        "",
        "## 3. Output Verification Table",
        "",
        "Upon successful execution, the following primary artifacts and metrics will be produced:",
        "",
        "| Artifact / Metric | Expected Value | Location | Verification Script |",
        "|---|---|---|---|",
        "| **CONUS Streamgage Panel** | 54 gauges (29 Ref / 25 Non-Ref) | `project/chunks/chunk02/full_panel.json` | `source/acquisition/verify_full_panel.py` |",
        "| **Pretraining Windows** | 9,760 windows (32 train basins) | `project/chunks/chunk04/pretrain_history.json` | `source/model/verify_encoder_convergence.py` |",
        "| **Model Parameters** | 146,950 parameters | `project/chunks/chunk04/c_encoder_pretrained.pt` | `source/model/verify_encoder_convergence.py` |",
        f"| **Score-A Test AUC-ROC** | ${final_results['primary_auc_pooled']:.4f}$ [95% CI: {final_results['primary_auc_pooled_ci95'][0]:.4f}, {final_results['primary_auc_pooled_ci95'][1]:.4f}] | `project/chunks/chunk07/data/discrimination_results.json` | `source/stats/eval_discrimination.py` |",
        f"| **H2 Lead-Time Verdict** | {final_results['h2_verdict']} ({final_results['h2_primary_detection_count']}/{final_results['h2_eligible_event_denominator']} primary detections, {final_results['h2_primary_median_lead_hours']:.1f}h median) | `project/chunks/chunk07/data/lead_time_survival_results.json` | `source/stats/eval_lead_time_survival.py` |",
        f"| **NWM Retrospective Baseline** | $\\text{{AUC}} = {final_results['nwm_auc_pooled']:.4f}$ | `project/chunks/chunk07/data/discrimination_results.json` | `source/stats/eval_discrimination.py` |",
        f"| **Supervised EA-LSTM (100%)** | $\\text{{AUC}} = {final_results['ea_lstm_auc_pooled']:.4f}$ | `project/chunks/chunk07/data/discrimination_results.json` | `source/stats/eval_discrimination.py` |",
        "| **Bootstrap Iterations** | $B = 10,000$ resamples | `project/chunks/chunk07/data/discrimination_results.json` | `source/stats/eval_discrimination.py` |",
        "| **Streamflow Holdout Drop** | $\\Delta \\text{AUC} = -0.0231$ | `project/chunks/chunk08/sensor_ablation_summary.json` | `source/ablation/sensor_ablation.py` |",
        "| **Hybrid vs TCN Delta** | $\\Delta \\text{AUC} = +0.0025$ | `project/chunks/chunk08/architecture_ablation_summary.json` | `source/ablation/architecture_ablation.py` |",
        "",
        "---",
        "",
        "## 4. Path Independence & Zero Leakage Compliance",
        "",
        "Per `INV-012` and Factory Rule `D-017`, this repository contains **zero hardcoded personal absolute paths**. All data loading, feature caching, model checkpointing, and evaluation metrics resolve dynamically relative to the repository root directory via `source/utils/config.py`."
    ]

    reproducibility_md = "\n".join(reproducibility_lines)
    reproducibility_path = REPO_ROOT / "REPRODUCIBILITY.md"

    with open(reproducibility_path, "w", encoding="utf-8") as f:
        f.write(reproducibility_md)

    logger.info(f"REPRODUCIBILITY.md written to {reproducibility_path}.")

    # Scan for any absolute path leaks in REPRODUCIBILITY.md
    from factory.gatekeeper import _scan_local_paths
    path_leaks = _scan_local_paths([reproducibility_path])
    if path_leaks:
        for leak in path_leaks:
            logger.error(leak)
        raise ValueError(f"Found {len(path_leaks)} absolute path leaks in REPRODUCIBILITY.md!")

    logger.info("REPRODUCIBILITY.md path leak scan: 0 leaks found (PASS).")
    return {
        "status": "PASS",
        "reproducibility_md": str(reproducibility_path),
        "manifest_path": str(manifest_path),
        "total_stages": len(stages)
    }


def main() -> None:
    generate_replication_package()


if __name__ == "__main__":
    main()
