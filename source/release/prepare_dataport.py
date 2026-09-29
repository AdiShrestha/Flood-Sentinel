"""IEEE DataPort and Open Science Deposit Packaging Engine (C09-03).

Catalogs all benchmark datasets, computes SHA-256 cryptographic checksums,
and generates IEEE DataPort deposit metadata and schema documentation.
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import (
    REPO_ROOT,
    PROJECT_DIR,
    CHUNKS_DIR,
    CHUNK09_DIR
)
from source.utils.logging_config import get_logger

logger = get_logger("prepare_dataport")


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 cryptographic hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def build_dataport_package() -> Dict[str, Any]:
    """Catalog benchmark datasets and generate IEEE DataPort release package."""
    logger.info("Building IEEE DataPort & Open Science Deposit Package (C09-03)...")

    # Key dataset files to catalog
    catalog_targets = [
        # Metadata
        {"path": PROJECT_DIR / "chunks/chunk02/full_panel.json", "category": "metadata", "desc": "54-streamgage CONUS panel metadata"},
        {"path": PROJECT_DIR / "key_facts.md", "category": "metadata", "desc": "Pre-registered numerical key facts"},
        {"path": REPO_ROOT / "source/feature/latency_registry.json", "category": "metadata", "desc": "Sensor publication latency registry"},
        
        # Features & Splits
        {"path": PROJECT_DIR / "chunks/chunk03/data/feature_matrix_train.parquet", "category": "features", "desc": "Pretraining feature matrix (Train)"},
        {"path": PROJECT_DIR / "chunks/chunk03/data/feature_matrix_val.parquet", "category": "features", "desc": "Feature matrix (Validation)"},
        {"path": PROJECT_DIR / "chunks/chunk03/data/feature_matrix_test.parquet", "category": "features", "desc": "Feature matrix (Test)"},
        
        # Pretrained Model
        {"path": PROJECT_DIR / "chunks/chunk04/checkpoints/c_encoder_pretrained.pt", "category": "model", "desc": "Pretrained C-ENCODER PyTorch weights"},
        {"path": PROJECT_DIR / "chunks/chunk04/pretraining_summary.json", "category": "model", "desc": "Pretraining loss convergence log"},
        
        # Precursor Scores
        {"path": PROJECT_DIR / "chunks/chunk05/calibration_params.json", "category": "scores", "desc": "Pre-evaluation calibration parameters"},
        {"path": PROJECT_DIR / "chunks/chunk05/data/score_a_test.parquet", "category": "scores", "desc": "Score-A Reconstruction Error (Test)"},
        {"path": PROJECT_DIR / "chunks/chunk05/data/score_b_test.parquet", "category": "scores", "desc": "Score-B Latent Distance (Test)"},
        {"path": PROJECT_DIR / "chunks/chunk05/data/score_c_test.parquet", "category": "scores", "desc": "Score-C Latent Transition (Test)"},
        
        # Baselines
        {"path": PROJECT_DIR / "chunks/chunk06/threshold_registry.json", "category": "baselines", "desc": "Validation alert threshold registry"},
        {"path": PROJECT_DIR / "chunks/chunk06/data/baseline_nwm_retro_test.parquet", "category": "baselines", "desc": "NWM Retrospective v3.0 baseline (Test)"},
        {"path": PROJECT_DIR / "chunks/chunk06/data/baseline_stat_test.parquet", "category": "baselines", "desc": "Statistical baselines (Test)"},
        {"path": PROJECT_DIR / "chunks/chunk06/data/baseline_learn_test.parquet", "category": "baselines", "desc": "Unsupervised ML baselines (Test)"},
        {"path": PROJECT_DIR / "chunks/chunk06/data/baseline_sup_test.parquet", "category": "baselines", "desc": "Supervised EA-LSTM baseline (Test)"},
        {"path": PROJECT_DIR / "chunks/chunk06/data/label_budget_sweep_results.parquet", "category": "baselines", "desc": "EA-LSTM label budget efficiency sweep"},
        
        # Evaluation & Hypothesis Tables
        {"path": PROJECT_DIR / "chunks/chunk07/data/evaluation_event_matrix.parquet", "category": "evaluation", "desc": "Collapsed event evaluation matrix"},
        {"path": PROJECT_DIR / "chunks/chunk07/data/discrimination_table.parquet", "category": "evaluation", "desc": "Per-comparator discrimination metrics"},
        {"path": PROJECT_DIR / "chunks/chunk07/data/survival_curves.parquet", "category": "evaluation", "desc": "Kaplan-Meier survival lead-time curves"},
        {"path": PROJECT_DIR / "chunks/chunk07/data/discrimination_results.json", "category": "evaluation", "desc": "Discrimination hypothesis test results"},
        {"path": PROJECT_DIR / "chunks/chunk07/data/lead_time_survival_results.json", "category": "evaluation", "desc": "Survival lead-time analysis results"},
        
        # Ablations
        {"path": PROJECT_DIR / "chunks/chunk08/data/sensor_ablation_results.parquet", "category": "ablations", "desc": "Sensor holdout ablation results"},
        {"path": PROJECT_DIR / "chunks/chunk08/data/architecture_ablation_results.parquet", "category": "ablations", "desc": "Architecture ablation results"},
        {"path": PROJECT_DIR / "chunks/chunk08/data/causal_masking_ablation_results.parquet", "category": "ablations", "desc": "Causal masking ablation results"},
        {"path": PROJECT_DIR / "chunks/chunk08/data/hyperparameter_sensitivity_results.parquet", "category": "ablations", "desc": "Hyperparameter sensitivity grid"}
    ]

    file_records = []
    total_bytes = 0

    for item in catalog_targets:
        p = item["path"]
        if not p.exists():
            logger.warning(f"File not found during cataloging: {p}")
            continue

        size_b = p.stat().st_size
        total_bytes += size_b
        sha256 = compute_sha256(p)
        
        # Compute row count for parquet files
        row_cnt = None
        if p.suffix == ".parquet":
            try:
                df = pd.read_parquet(p)
                row_cnt = len(df)
            except Exception as e:
                logger.error(f"Error reading parquet row count for {p}: {e}")

        rel_path = p.relative_to(REPO_ROOT).as_posix()
        file_records.append({
            "relative_path": rel_path,
            "filename": p.name,
            "category": item["category"],
            "description": item["desc"],
            "size_bytes": size_b,
            "row_count": row_cnt,
            "sha256_checksum": sha256
        })

    # Save dataport_manifest.json
    CHUNK09_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = CHUNK09_DIR / "dataport_manifest.json"
    manifest_data = {
        "dataset_title": "Flood Sentinel: Self-Supervised Multi-Sensor Precursor Benchmark for CONUS Hydrological Extremes",
        "version": "1.0.0",
        "license": "Creative Commons Attribution 4.0 International (CC-BY 4.0)",
        "spatial_coverage": "Contiguous United States (54 USGS Streamgages across 14 HUC Regions)",
        "temporal_coverage": "1990-01-01 to 2023-12-31 (34 continuous years)",
        "total_cataloged_files": len(file_records),
        "total_size_bytes": total_bytes,
        "files": file_records
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    logger.info(f"DataPort manifest written to {manifest_path} ({len(file_records)} files, {total_bytes:,} bytes).")

    # Generate IEEE DataPort Deposit Documentation Markdown
    lines = [
        "# IEEE DataPort Dataset Deposit Specification — Flood Sentinel",
        "",
        "**Dataset Title:** Flood Sentinel: Self-Supervised Multi-Sensor Precursor Benchmark for CONUS Hydrological Extremes  ",
        "**Persistent Identifier (DOI):** `10.21227/flood-sentinel-2026` *(IEEE DataPort Reserved)*  ",
        "**Dataset Version:** `1.0.0`  ",
        "**License:** [Creative Commons Attribution 4.0 International (CC-BY 4.0)](https://creativecommons.org/licenses/by/4.0/)  ",
        "",
        "---",
        "",
        "## 1. Abstract & Dataset Description",
        "",
        "The **Flood Sentinel Benchmark Dataset** provides standardized multi-sensor Earth-observation time series, physics-informed static basin attributes, pre-registered precursor anomaly scores, and comparative hydrological baselines across 54 representative streamgages in the Contiguous United States (CONUS) spanning 34 continuous years (1990–2023).",
        "",
        "Unlike standard point-in-time discharge records, this benchmark features:",
        "- **Multi-Sensor Synchronized Observations:** Integrated USGS daily discharge and gage height, gridMET daily precipitation and temperature, and NOAA SNODAS Snow Water Equivalent.",
        "- **Authoritative Event Delineation:** Primary ground truth derived from official NOAA National Water Prediction Service (NWPS) Action, Minor, Moderate, and Major flood stages.",
        "- **Information-State Realism:** Rigorous adherence to federal publication latencies (0h provisional USGS, 14h NRT gridMET, 24h SNODAS SWE) preventing operational data leakage.",
        "- **Standardized Evaluation Matrix:** 787 collapsed event instances across 11 held-out test basins for leak-free, pseudoreplication-free statistical benchmarking.",
        "",
        "---",
        "",
        "## 2. Spatial & Temporal Coverage",
        "",
        "- **Spatial Domain:** 54 USGS streamgages spanning 14 HUC 2-digit Water Resource Regions.",
        "- **Hydrological Regimes:** 27 GAGES-II Reference catchments (unregulated natural flow) and 27 Non-Reference catchments (anthropogenically regulated with upstream dams).",
        "- **Drainage Area Tiers:** Small ($< 500\\text{ km}^2$, 18 basins), Medium ($500–5,000\\text{ km}^2$, 20 basins), and Large ($> 5,000\\text{ km}^2$, 16 basins).",
        "- **Temporal Span:** January 1, 1990 to December 31, 2023 (12,418 daily timestamps per station; 670,572 station-days).",
        "",
        "---",
        "",
        "## 3. Dataset File Catalog & SHA-256 Checksums",
        "",
        "| Category | Relative File Path | Size (Bytes) | Row Count | SHA-256 Checksum (Hex) |",
        "|---|---|---|---|---|"
    ]

    for rec in file_records:
        row_str = str(rec["row_count"]) if rec["row_count"] is not None else "N/A"
        lines.append(
            f"| `{rec['category']}` | `{rec['relative_path']}` | {rec['size_bytes']:,} | {row_str} | `{rec['sha256_checksum'][:16]}...` |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 4. Primary Variables & Data Dictionary",
        "",
        "### A. Multi-Sensor Time Series (`feature_matrix_*.parquet`)",
        "- `discharge_cfs`: USGS instantaneous daily mean streamflow ($ft^3/s$).",
        "- `gage_height_ft`: USGS river stage ($ft$).",
        "- `precipitation_amount_mm`: gridMET daily total precipitation ($mm$).",
        "- `air_temperature_minimum_k`: gridMET daily minimum surface air temperature ($K$).",
        "- `air_temperature_maximum_k`: gridMET daily maximum surface air temperature ($K$).",
        "- `snodas_swe_mm`: NOAA/NSIDC daily Snow Water Equivalent ($mm$).",
        "",
        "### B. Precursor Anomaly Scores (`score_*.parquet`)",
        "- `score_a`: C-ENCODER multi-sensor masked reconstruction error scaled by pre-evaluation historical IQR.",
        "- `score_b`: Latent representation embedding trajectory distance from historical running median.",
        "- `score_c`: Latent future state transition error.",
        "",
        "### C. Baseline Benchmarks (`baseline_*.parquet`)",
        "- `baseline_nwm_retro`: NOAA National Water Model Retrospective v3.0 unassimilated channel routing simulation.",
        "- `baseline_persistence_roc`: 1-day streamflow rate-of-change.",
        "- `baseline_climatology_exceedance`: Day-of-year rolling 15-day 95th percentile exceedance.",
        "- `baseline_page_cusum`: Page (1954) cumulative sum changepoint detector.",
        "- `baseline_iforest`: Scikit-learn multi-channel Isolation Forest anomaly score.",
        "- `baseline_lstm_ae`: PyTorch 2-layer LSTM-Autoencoder reconstruction error.",
        "- `baseline_ea_lstm_sup`: Entity-Aware LSTM (Kratzert et al., 2019) supervised flood probability.",
        "",
        "---",
        "",
        "## 5. Terms of Use & Citation",
        "",
        "This dataset is published under the **Creative Commons Attribution 4.0 International (CC-BY 4.0)** license. When using this dataset in research publications, please cite:",
        "",
        "```bibtex",
        "@article{floodsentinel2026,",
        "  title={Self-Supervised Multi-Sensor Neural Representations for Hydrological Flood Precursor Detection Across CONUS Basins},",
        "  author={Flood Sentinel Research Team},",
        "  journal={IEEE Access},",
        "  year={2026},",
        "  doi={10.21227/flood-sentinel-2026}",
        "}",
        "```"
    ])

    deposit_doc_md = "\n".join(lines)
    deposit_doc_path = CHUNK09_DIR / "ieee_dataport_deposit.md"

    with open(deposit_doc_path, "w", encoding="utf-8") as f:
        f.write(deposit_doc_md)

    logger.info(f"IEEE DataPort deposit document written to {deposit_doc_path}.")
    return manifest_data


def main() -> None:
    build_dataport_package()


if __name__ == "__main__":
    main()
