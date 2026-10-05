#!/usr/bin/env python3
"""Executable runner for development pilot optimization, comparator ladder, and compute ledger.

Usage:
    PYTHONPATH=source python3 source/runners/run_pilots.py
"""
from __future__ import annotations

import csv
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time

import torch

from flood_sentinel.adapters.recompute import (
    recompute_auroc,
    recompute_average_precision,
    recompute_binary_metrics,
)
from flood_sentinel.dataset import CausalHydroDataset, create_dataloader
from flood_sentinel.pilots import (
    EALSTMPilotTrainer,
    EWMACUSUMComparator,
    HardwareProfile,
    MaskedHydroPilotTrainer,
    PersistenceComparator,
    TabularRidgeComparator,
)
from flood_sentinel.scaler import PersistentScaler


def run_all_pilots() -> dict[str, Any]:
    root = Path(__file__).resolve().parent.parent.parent
    cohort_path = root / "data/cohort.csv"
    src_path = root / "data/source_records.csv"

    print("==================================================================")
    print(" FLOOD SENTINEL P07: DEVELOPMENT PILOTS & COMPUTE LEDGER")
    print("==================================================================")

    # 1. Dataset Loading & Train-Only Normalization
    print("\n[1] Constructing causal datasets & fitting train-only scaler...")
    train_ds_raw = CausalHydroDataset(cohort_path, src_path, split="train")
    raw_train_mat = train_ds_raw.get_raw_observations_matrix()
    scaler = PersistentScaler.fit(raw_train_mat, train_ds_raw.channels, split="train")

    train_ds = CausalHydroDataset(cohort_path, src_path, split="train", scaler=scaler)
    val_ds = CausalHydroDataset(cohort_path, src_path, split="validation", scaler=scaler)

    train_loader = create_dataloader(train_ds, batch_size=2, shuffle=True)
    val_loader = create_dataloader(val_ds, batch_size=2, shuffle=False)

    val_labels = [val_ds[i].label for i in range(len(val_ds))]
    print(f"    Train samples: {len(train_ds)}, Validation samples: {len(val_ds)}")
    print(f"    Validation label distribution: {val_labels}")

    ledger: dict[str, Any] = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "platform": sys.platform,
        "python_version": sys.version.split()[0],
        "torch_version": torch.__version__,
        "device": "cpu",
        "comparators": {},
    }

    # =====================================================================
    # Tier 1: True Persistence Baseline
    # =====================================================================
    print("\n[2] Tier 1: True Persistence Baseline...")
    t0 = time.perf_counter()
    p_scores = PersistenceComparator.evaluate_dataset(val_ds)
    p_time = max(time.perf_counter() - t0, 1e-6)
    p_auc = recompute_auroc(val_labels, p_scores)
    p_ap = recompute_average_precision(val_labels, p_scores)
    print(f"    Validation AUROC: {p_auc:.4f}, AP: {p_ap:.4f}, Time: {p_time*1000:.2f} ms")
    ledger["comparators"]["persistence"] = {
        "auroc": p_auc,
        "average_precision": p_ap,
        "runtime_seconds": p_time,
        "parameters": 0,
    }

    # =====================================================================
    # Tier 2: Continuous EWMA-CUSUM Baseline
    # =====================================================================
    print("\n[3] Tier 2: Continuous EWMA-CUSUM Baseline...")
    t0 = time.perf_counter()
    cusum_model = EWMACUSUMComparator.fit_from_dataset(train_ds)
    cusum_scores = cusum_model.evaluate_dataset(val_ds)
    cusum_time = max(time.perf_counter() - t0, 1e-6)
    c_auc = recompute_auroc(val_labels, cusum_scores)
    c_ap = recompute_average_precision(val_labels, cusum_scores)
    print(f"    Validation AUROC: {c_auc:.4f}, AP: {c_ap:.4f}, Time: {cusum_time*1000:.2f} ms")
    ledger["comparators"]["ewma_cusum"] = {
        "auroc": c_auc,
        "average_precision": c_ap,
        "runtime_seconds": cusum_time,
        "parameters": 2,  # mean, scale
    }

    # =====================================================================
    # Tier 3: Tabular Ridge Logistic Baseline
    # =====================================================================
    print("\n[4] Tier 3: Tabular Ridge Logistic Baseline...")
    t0 = time.perf_counter()
    ridge_model = TabularRidgeComparator(l2_reg=1.0)
    ridge_model.fit(train_ds)
    ridge_scores = ridge_model.evaluate_dataset(val_ds)
    ridge_time = max(time.perf_counter() - t0, 1e-6)
    r_auc = recompute_auroc(val_labels, ridge_scores)
    r_ap = recompute_average_precision(val_labels, ridge_scores)
    print(f"    Validation AUROC: {r_auc:.4f}, AP: {r_ap:.4f}, Time: {ridge_time*1000:.2f} ms")
    ledger["comparators"]["tabular_ridge"] = {
        "auroc": r_auc,
        "average_precision": r_ap,
        "runtime_seconds": ridge_time,
        "parameters": len(ridge_model.feature_names) + 1,
    }

    # =====================================================================
    # Tier 4: Supervised EA-LSTM Baseline
    # =====================================================================
    print("\n[5] Tier 4: Supervised EA-LSTM Baseline...")
    ea_trainer = EALSTMPilotTrainer(dynamic_dim=2, static_dim=4, hidden_dim=16, lr=1e-3)
    ea_traces, ea_meta, ea_hw = ea_trainer.train_pilot(
        train_loader, val_loader, max_epochs=10, patience=3
    )
    ea_scores = ea_trainer.evaluate_dataset(val_loader)
    ea_auc = recompute_auroc(val_labels, ea_scores)
    ea_ap = recompute_average_precision(val_labels, ea_scores)
    print(f"    Trained {ea_meta['total_epochs']} epochs, Best Epoch: {ea_meta['best_epoch']}, Best Val Loss: {ea_meta['best_val_loss']:.4f}")
    print(f"    Validation AUROC: {ea_auc:.4f}, AP: {ea_ap:.4f}")
    print(f"    Hardware: {ea_hw.wall_clock_seconds:.3f} s, Peak RSS: {ea_hw.peak_rss_mb:.1f} MB, Params: {ea_hw.total_parameters}")
    ledger["comparators"]["ea_lstm"] = {
        "auroc": ea_auc,
        "average_precision": ea_ap,
        "best_epoch": ea_meta["best_epoch"],
        "best_val_loss": ea_meta["best_val_loss"],
        "traces": [asdict(t) for t in ea_traces],
        "hardware": asdict(ea_hw),
    }

    # =====================================================================
    # Tiers 5 & 6: Proposed Masked Hydro Model (Score A & Score B)
    # =====================================================================
    print("\n[6] Tiers 5 & 6: Proposed Masked Hydro Foundation Model...")
    mh_trainer = MaskedHydroPilotTrainer(
        in_channels=2, d_model=16, tcn_layers=1, transformer_layers=1, n_heads=2, lr=1e-3
    )
    mh_traces, mh_meta, mh_hw = mh_trainer.train_pilot(
        train_loader, val_loader, max_epochs=10, patience=3, corruption_rate=0.25
    )
    score_a = mh_trainer.evaluate_score_a(val_loader)
    score_b = mh_trainer.evaluate_score_b(train_loader, val_loader)

    sa_auc = recompute_auroc(val_labels, score_a)
    sa_ap = recompute_average_precision(val_labels, score_a)
    sb_auc = recompute_auroc(val_labels, score_b)
    sb_ap = recompute_average_precision(val_labels, score_b)

    print(f"    Trained {mh_meta['total_epochs']} epochs, Best Epoch: {mh_meta['best_epoch']}, Best Val Masked Loss: {mh_meta['best_val_loss']:.4f}")
    print(f"    Score A (Leave-Channel-Out): AUROC: {sa_auc:.4f}, AP: {sa_ap:.4f}")
    print(f"    Score B (Latent Covariance):  AUROC: {sb_auc:.4f}, AP: {sb_ap:.4f}")
    print(f"    Hardware: {mh_hw.wall_clock_seconds:.3f} s, Peak RSS: {mh_hw.peak_rss_mb:.1f} MB, Params: {mh_hw.total_parameters}")
    ledger["comparators"]["masked_hydro_score_a"] = {
        "auroc": sa_auc,
        "average_precision": sa_ap,
        "best_epoch": mh_meta["best_epoch"],
        "best_val_loss": mh_meta["best_val_loss"],
        "traces": [asdict(t) for t in mh_traces],
        "hardware": asdict(mh_hw),
    }
    ledger["comparators"]["masked_hydro_score_b"] = {
        "auroc": sb_auc,
        "average_precision": sb_ap,
        "best_epoch": mh_meta["best_epoch"],
        "best_val_loss": mh_meta["best_val_loss"],
        "hardware": asdict(mh_hw),
    }

    # =====================================================================
    # Summary Table
    # =====================================================================
    print("\n==================================================================")
    print(" PILOT EVALUATION SUMMARY (VALIDATION SPLIT)")
    print("==================================================================")
    print(f"{'Comparator':<30} | {'AUROC':<8} | {'AP':<8} | {'Params':<8} | {'Runtime (s)':<10}")
    print("-" * 75)
    for name, res in ledger["comparators"].items():
        p_count = res.get("parameters") or res.get("hardware", {}).get("total_parameters", 0)
        rt = res.get("runtime_seconds") or res.get("hardware", {}).get("wall_clock_seconds", 0.0)
        print(f"{name:<30} | {res['auroc']:<8.4f} | {res['average_precision']:<8.4f} | {p_count:<8} | {rt:<10.3f}")

    print("\n==================================================================")
    print(" ALL PILOT RUNS COMPLETE — HARDWARE PROFILES RECORDED")
    print("==================================================================")
    return ledger


if __name__ == "__main__":
    run_all_pilots()
