# Reproducibility Guide — Flood Sentinel

This guide provides complete, step-by-step instructions to reproduce all empirical findings, neural models, baseline comparators, statistical hypothesis tests, and ablation studies reported in:

> **"Self-Supervised Multi-Sensor Neural Representations for Hydrological Flood Precursor Detection Across CONUS Basins"**

---

## 1. System Requirements & Environment Setup

### Hardware Requirements
- **Processor:** Standard x86_64 or Apple Silicon CPU (Multi-core recommended, $\ge 4$ cores).
- **Memory:** Minimum 8 GB RAM (16 GB recommended).
- **Storage:** $\approx 2\text{ GB}$ free disk space for raw data cache, feature arrays, and checkpoints.
- **Compute Budget:** ~2.0 hours total execution time on standard CPU hardware (no GPU required).

### Software Requirements
- **Operating System:** Linux (Ubuntu 20.04+), macOS (12.0+), or Windows (WSL2).
- **Python:** Python 3.10, 3.11, or 3.12.

### Environment Installation
Clone the repository and install the exact pinned scientific dependencies:

```bash
# Clone repository
git clone https://github.com/flood-sentinel/flood-sentinel.git
cd flood-sentinel

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install pinned dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 2. End-to-End Sequential Replication Pipeline

Execute the following stages in sequence from the repository root:

### Stage 1: Earth Observation & Hydrometric Data Acquisition (Chunk 02)
Acquires 34-year records (1990–2023) for all 54 CONUS panel streamgages across USGS streamflow, gridMET meteorology, SNODAS snowpack, GAGES-II/NID static attributes, and NOAA NWPS flood stages:
```bash
python3 source/acquisition/verify_full_panel.py
python3 source/acquisition/verify_usgs_full.py
python3 source/acquisition/verify_gridmet_full.py
python3 source/acquisition/verify_snodas_full.py
python3 source/acquisition/verify_attributes_full.py
python3 source/acquisition/verify_thresholds_full.py
python3 source/acquisition/verify_nwm_retro_full.py
python3 source/acquisition/verify_events_full.py
python3 source/gate/run_reality_gate.py --manifest-dir project/chunks/chunk02/manifests/
```

### Stage 2: Feature Engineering & Latency Registry (Chunk 03)
Validates physical sensor publication latencies and temporal feature windowing:
```bash
python3 source/feature/verify_latency_registry.py
```

### Stage 3: C-ENCODER Self-Supervised Pretraining (Chunk 04)
Pretrains the 146,950-parameter hybrid Dilated Causal TCN + Transformer on 9,760 unlabeled multi-sensor temporal windows ($r = 0.15$ dynamic masking):
```bash
python3 source/model/c_encoder.py
python3 source/model/pretrain_encoder.py --epochs 10 --batch-size 64
python3 source/model/verify_encoder_convergence.py
```

### Stage 4: Calibration & Precursor Anomaly Scoring (Chunk 05)
Calibrates pre-evaluation gauge statistics and extracts precursor score streams (Score-A reconstruction, Score-B latent distance, Score-C latent transition):
```bash
python3 source/scorer/calibration.py
python3 source/scorer/score_a.py
python3 source/scorer/score_b.py
python3 source/scorer/score_c.py
python3 source/scorer/verify_calibration_isolation.py
```

### Stage 5: Comparative Baseline Benchmark Suite (Chunk 06)
Trains and evaluates all physical, statistical, unsupervised ML, and supervised deep learning comparators, including the 26-condition EA-LSTM label sweep:
```bash
python3 source/baseline/baseline_op.py
python3 source/baseline/baseline_stat.py
python3 source/baseline/baseline_learn.py
python3 source/baseline/baseline_sup.py
python3 source/baseline/label_budget_sweep.py
python3 source/baseline/threshold_registry.py
python3 source/baseline/verify_all_baselines.py
```

### Stage 6: Statistical Evaluation & Hypothesis Testing (Chunk 07)
Executes window-event collapse, discrimination batteries with Wilcoxon FDR tests, Kaplan-Meier lead-time survival analysis, and sample adequacy verification:
```bash
python3 source/stats/collapse_events.py
python3 source/stats/eval_discrimination.py
python3 source/stats/eval_lead_time_survival.py
python3 source/stats/eval_sample_adequacy.py
python3 source/stats/verify_chunk07_reality_gate.py
```

### Stage 7: Ablation Studies & Sensitivity Grids (Chunk 08)
Runs physical sensor holdout, neural architecture comparisons, causal attention validation, hyperparameter sweeps, and title claim audits:
```bash
python3 source/ablation/sensor_ablation.py
python3 source/ablation/architecture_ablation.py
python3 source/ablation/causal_masking_ablation.py
python3 source/ablation/hyperparameter_sensitivity.py
python3 source/ablation/audit_title_claims.py
python3 source/ablation/verify_chunk08_reality_gate.py
```

### Stage 8: Release Packaging & Integrity Certification (Chunk 09)
Verifies machine-readable key-fact consistency and release integrity:
```bash
python3 source/release/verify_key_facts.py
python3 source/release/package_replication.py
```

### Stage 9: Publication Figures & Synthesis Verification (Chunk 10)
Generates the complete 7-figure publication vector SVG suite and runs mechanical gatekeepers:
```bash
# Generate complete 7-figure publication suite
for f in fig1_basin_map fig2_roc_curves fig3_per_basin_auc_distribution fig4_km_survival_curves \
         fig5_label_budget_curve fig6_ablation_bars fig7_architecture_diagram; do
  python3 source/figures/${f}.py --out project/chunks/chunk10/figures/${f#fig?_}.svg
done

# Run mechanical gatekeeper and parity verifiers
python3 source/release/verify_sc008.py \
  --manuscript project/chunks/chunk09/manuscript_draft.md \
  --venue-requirements project/venue_requirements.md \
  --key-facts project/key_facts.md \
  --manifest project/chunks/chunk10/final_results_manifest.json
python3 source/release/verify_references.py --manuscript project/chunks/chunk09/manuscript_draft.md
python3 source/release/verify_baseline_parity.py --out project/chunks/chunk10/baseline_parity_audit.md
python3 source/release/rehash_dataport_manifest.py --verify
python3 source/release/verify_final_synthesis.py
```

---

## 3. Output Verification Table

Upon successful execution, the following primary artifacts and metrics will be produced:

| Artifact / Metric | Expected Value | Location | Verification Script |
|---|---|---|---|
| **CONUS Streamgage Panel** | 54 gauges (29 Ref / 25 Non-Ref) | `project/chunks/chunk02/full_panel.json` | `source/acquisition/verify_full_panel.py` |
| **Pretraining Windows** | 9,760 windows (32 train basins) | `project/chunks/chunk04/pretrain_history.json` | `source/model/verify_encoder_convergence.py` |
| **Model Parameters** | 146,950 parameters | `project/chunks/chunk04/c_encoder_pretrained.pt` | `source/model/verify_encoder_convergence.py` |
| **Score-A Test AUC-ROC** | $0.8296$ [95% CI: 0.6885, 0.9642] | `project/chunks/chunk07/data/discrimination_results.json` | `source/stats/eval_discrimination.py` |
| **H2 Lead-Time Verdict** | FALSIFIED (0/8 primary detections, 0.0h median) | `project/chunks/chunk07/data/lead_time_survival_results.json` | `source/stats/eval_lead_time_survival.py` |
| **NWM Retrospective Baseline** | $\text{AUC} = 0.9070$ | `project/chunks/chunk07/data/discrimination_results.json` | `source/stats/eval_discrimination.py` |
| **Supervised EA-LSTM (100%)** | $\text{AUC} = 0.8129$ | `project/chunks/chunk07/data/discrimination_results.json` | `source/stats/eval_discrimination.py` |
| **Bootstrap Iterations** | $B = 10,000$ resamples | `project/chunks/chunk07/data/discrimination_results.json` | `source/stats/eval_discrimination.py` |
| **Streamflow Holdout Drop** | $\Delta \text{AUC} = -0.0231$ | `project/chunks/chunk08/sensor_ablation_summary.json` | `source/ablation/sensor_ablation.py` |
| **Hybrid vs TCN Delta** | $\Delta \text{AUC} = +0.0025$ | `project/chunks/chunk08/architecture_ablation_summary.json` | `source/ablation/architecture_ablation.py` |
| **Publication Figure Suite** | 7 Vector SVGs | `project/chunks/chunk10/figures/` | `source/figures/` (C10-11) |
| **DataPort Deposit Manifest** | 27 cataloged files (0 stale hashes) | `project/chunks/chunk09/dataport_manifest.json` | `source/release/rehash_dataport_manifest.py` |

---

## 4. Path Independence & Zero Leakage Compliance

Per `INV-012` and Factory Rule `D-017`, this repository contains **zero hardcoded personal absolute paths**. All data loading, feature caching, model checkpointing, and evaluation metrics resolve dynamically relative to the repository root directory via `source/utils/config.py`.