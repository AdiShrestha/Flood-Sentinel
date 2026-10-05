#!/usr/bin/env python3
"""Hardware measurement, inference benchmarking, and reproducibility audit runner.

Measures actual CPU runtime, latency percentiles, sustained inference throughput,
and peak memory consumption across all 7 hydrological model families on host hardware.
Validates bitwise clean replay reproduction and cross-artifact metric traceability.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable

# Ensure source is on sys.path
SOURCE_DIR = Path(__file__).resolve().parents[1]
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

import numpy as np
import torch
from torch.utils.data import DataLoader

from flood_sentinel.dataset import CausalHydroDataset, create_dataloader
from flood_sentinel.hardware import (
    benchmark_inference,
    count_parameters,
    get_current_rss_mb,
    get_host_hardware_info,
)
from flood_sentinel.model import CausalForecastingHead, CausalHydroEncoder
from flood_sentinel.pilots import (
    EALSTMPilotTrainer,
    EWMACUSUMComparator,
    MaskedHydroPilotTrainer,
    PersistenceComparator,
    TabularRidgeComparator,
)
from flood_sentinel.reproducibility import audit_run_replay, compare_prediction_series
from flood_sentinel.scaler import PersistentScaler
try:
    from runners.run_experiment import TrainPlattCalibrator, parse_model_family
    from runners.run_postprocessing import find_latest_runs_dir
except ImportError:
    from source.runners.run_experiment import TrainPlattCalibrator, parse_model_family
    from source.runners.run_postprocessing import find_latest_runs_dir


def setup_datasets(root: Path) -> tuple[PersistentScaler, CausalHydroDataset, CausalHydroDataset, CausalHydroDataset]:
    """Load cohorts and fit train-only persistent normalizer."""
    cohort_path = root / "data/cohort.csv"
    src_path = root / "data/source_records.csv"

    train_ds_raw = CausalHydroDataset(cohort_path, src_path, split="train")
    scaler = PersistentScaler.fit(train_ds_raw.get_raw_observations_matrix(), train_ds_raw.channels, split="train")

    train_ds = CausalHydroDataset(cohort_path, src_path, split="train", scaler=scaler)
    val_ds = CausalHydroDataset(cohort_path, src_path, split="validation", scaler=scaler)
    test_ds = CausalHydroDataset(cohort_path, src_path, split="test", scaler=scaler)
    return scaler, train_ds, val_ds, test_ds


def benchmark_all_model_families(
    root: Path,
    runs_dir: Path,
    measured_trials: int = 50,
    warmup_trials: int = 10,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Execute hardware benchmarking trials across all 7 model families."""
    scaler, train_ds, val_ds, test_ds = setup_datasets(root)
    train_loader = create_dataloader(train_ds, batch_size=2, shuffle=False)
    test_loader_batch = create_dataloader(test_ds, batch_size=len(test_ds), shuffle=False)
    test_loader_single = create_dataloader(test_ds, batch_size=1, shuffle=False)
    train_labels = [train_ds[i].label for i in range(len(train_ds))]

    n_test = len(test_ds)
    single_sample = next(iter(test_loader_single))
    batch_sample = next(iter(test_loader_batch))

    family_results: dict[str, Any] = {}
    csv_rows: list[dict[str, Any]] = []

    # 1. Tier 1: Persistence
    pers_train = PersistenceComparator.evaluate_dataset(train_ds)
    pers_calibrator = TrainPlattCalibrator().fit(pers_train, train_labels)

    def pers_forward_single() -> list[float]:
        raw = PersistenceComparator.evaluate_dataset([test_ds[0]])
        return pers_calibrator.predict(raw)

    def pers_forward_batch() -> list[float]:
        raw = PersistenceComparator.evaluate_dataset(test_ds)
        return pers_calibrator.predict(raw)

    pers_single = benchmark_inference(pers_forward_single, n_samples=1, warmup_trials=warmup_trials, measured_trials=measured_trials)
    pers_batch = benchmark_inference(pers_forward_batch, n_samples=n_test, warmup_trials=warmup_trials, measured_trials=measured_trials)

    # 2. Tier 2: EWMA-CUSUM
    cusum = EWMACUSUMComparator.fit_from_dataset(train_ds)
    cusum_train = cusum.evaluate_dataset(train_ds)
    cusum_calibrator = TrainPlattCalibrator().fit(cusum_train, train_labels)

    def cusum_forward_single() -> list[float]:
        raw = cusum.evaluate_dataset([test_ds[0]])
        return cusum_calibrator.predict(raw)

    def cusum_forward_batch() -> list[float]:
        raw = cusum.evaluate_dataset(test_ds)
        return cusum_calibrator.predict(raw)

    cusum_single = benchmark_inference(cusum_forward_single, n_samples=1, warmup_trials=warmup_trials, measured_trials=measured_trials)
    cusum_batch = benchmark_inference(cusum_forward_batch, n_samples=n_test, warmup_trials=warmup_trials, measured_trials=measured_trials)

    # 3. Tier 3: Tabular Ridge
    ridge = TabularRidgeComparator(l2_reg=1.0)
    ridge.fit(train_ds)

    def ridge_forward_single() -> list[float]:
        return ridge.evaluate_dataset([test_ds[0]])

    def ridge_forward_batch() -> list[float]:
        return ridge.evaluate_dataset(test_ds)

    ridge_single = benchmark_inference(ridge_forward_single, n_samples=1, warmup_trials=warmup_trials, measured_trials=measured_trials)
    ridge_batch = benchmark_inference(ridge_forward_batch, n_samples=n_test, warmup_trials=warmup_trials, measured_trials=measured_trials)

    # 4. Tier 4: EA-LSTM
    ea_ckpt = runs_dir / "exp_ea_lstm_s42/attempt0001/checkpoint.pt"
    ea_trainer = EALSTMPilotTrainer(dynamic_dim=2, static_dim=4, hidden_dim=16)
    if ea_ckpt.is_file():
        ea_trainer.model.load_state_dict(torch.load(ea_ckpt, weights_only=False))
    ea_trainer.model.eval()

    def ea_forward_single() -> list[float]:
        return ea_trainer.evaluate_dataset(test_loader_single)

    def ea_forward_batch() -> list[float]:
        return ea_trainer.evaluate_dataset(test_loader_batch)

    ea_single = benchmark_inference(ea_forward_single, n_samples=1, warmup_trials=warmup_trials, measured_trials=measured_trials)
    ea_batch = benchmark_inference(ea_forward_batch, n_samples=n_test, warmup_trials=warmup_trials, measured_trials=measured_trials)

    # 5. Tier 5: Masked Hydro Score A
    mh_a_ckpt = runs_dir / "exp_masked_hydro_score_a_s42/attempt0001/checkpoint.pt"
    mh_a = MaskedHydroPilotTrainer(in_channels=2, d_model=16, lr=1e-3)
    if mh_a_ckpt.is_file():
        mh_a.model.load_state_dict(torch.load(mh_a_ckpt, weights_only=False))
    mh_a.model.eval()
    train_score_a = mh_a.evaluate_score_a(train_loader)
    cal_score_a = TrainPlattCalibrator().fit(train_score_a, train_labels)

    def mh_a_forward_single() -> list[float]:
        raw = mh_a.evaluate_score_a(test_loader_single)
        return cal_score_a.predict(raw)

    def mh_a_forward_batch() -> list[float]:
        raw = mh_a.evaluate_score_a(test_loader_batch)
        return cal_score_a.predict(raw)

    mh_a_single = benchmark_inference(mh_a_forward_single, n_samples=1, warmup_trials=warmup_trials, measured_trials=measured_trials)
    mh_a_batch = benchmark_inference(mh_a_forward_batch, n_samples=n_test, warmup_trials=warmup_trials, measured_trials=measured_trials)

    # 6. Tier 6: Masked Hydro Score B
    mh_b_ckpt = runs_dir / "exp_masked_hydro_score_b_s42/attempt0001/checkpoint.pt"
    mh_b = MaskedHydroPilotTrainer(in_channels=2, d_model=16, lr=1e-3)
    if mh_b_ckpt.is_file():
        mh_b.model.load_state_dict(torch.load(mh_b_ckpt, weights_only=False))
    mh_b.model.eval()
    train_score_b = mh_b.evaluate_score_b(train_loader, train_loader)
    cal_score_b = TrainPlattCalibrator().fit(train_score_b, train_labels)

    def mh_b_forward_single() -> list[float]:
        raw = mh_b.evaluate_score_b(train_loader, test_loader_single)
        return cal_score_b.predict(raw)

    def mh_b_forward_batch() -> list[float]:
        raw = mh_b.evaluate_score_b(train_loader, test_loader_batch)
        return cal_score_b.predict(raw)

    mh_b_single = benchmark_inference(mh_b_forward_single, n_samples=1, warmup_trials=warmup_trials, measured_trials=measured_trials)
    mh_b_batch = benchmark_inference(mh_b_forward_batch, n_samples=n_test, warmup_trials=warmup_trials, measured_trials=measured_trials)

    # 7. Supervised Benchmark: CausalForecastingHead
    cfh_ckpt = runs_dir / "exp_causal_forecasting_head_s42/attempt0001/checkpoint.pt"
    encoder = CausalHydroEncoder(in_channels=4, d_model=16, tcn_layers=1, transformer_layers=1, n_heads=2, d_ff=32, dropout=0.0)
    head = CausalForecastingHead(d_model=16, out_dim=1)
    if cfh_ckpt.is_file():
        c_dict = torch.load(cfh_ckpt, weights_only=False)
        encoder.load_state_dict(c_dict["encoder"])
        head.load_state_dict(c_dict["head"])
    encoder.eval()
    head.eval()

    # Pre-extracted tensors for single-sample and batch forward passes
    v_s = single_sample["values"]
    o_s = single_sample["observed"]
    inp_s = torch.cat((v_s - v_s[:, :1, :], o_s.float()), dim=-1)

    v_b = batch_sample["values"]
    o_b = batch_sample["observed"]
    inp_b = torch.cat((v_b - v_b[:, :1, :], o_b.float()), dim=-1)

    def cfh_forward_single() -> list[float]:
        with torch.no_grad():
            z = encoder(inp_s)
            p = torch.sigmoid(head(z).squeeze(-1))
            return [float(p.item())] if p.ndim == 0 else p.tolist()

    def cfh_forward_batch() -> list[float]:
        with torch.no_grad():
            z = encoder(inp_b)
            p = torch.sigmoid(head(z).squeeze(-1))
            return p.tolist()

    cfh_single = benchmark_inference(cfh_forward_single, n_samples=1, warmup_trials=warmup_trials, measured_trials=measured_trials)
    cfh_batch = benchmark_inference(cfh_forward_batch, n_samples=n_test, warmup_trials=warmup_trials, measured_trials=measured_trials)

    # Assembly mapping
    benchmarks = [
        ("persistence", pers_single, pers_batch, 2, "deterministic"),
        ("ewma_cusum", cusum_single, cusum_batch, 4, "deterministic"),
        ("tabular_ridge", ridge_single, ridge_batch, 10, "linear"),
        ("ea_lstm", ea_single, ea_batch, count_parameters(ea_trainer.model), "recurrent_neural"),
        ("masked_hydro_score_a", mh_a_single, mh_a_batch, count_parameters(mh_a.model), "tcn_autoencoder"),
        ("masked_hydro_score_b", mh_b_single, mh_b_batch, count_parameters(mh_b.model), "tcn_autoencoder"),
        ("causal_forecasting_head", cfh_single, cfh_batch, count_parameters((encoder, head)), "causal_tcn_transformer"),
    ]

    for name, single_res, batch_res, param_count, arch_type in benchmarks:
        family_results[name] = {
            "architecture_type": arch_type,
            "parameter_count": param_count,
            "single_sample_inference": single_res,
            "batch_inference": batch_res,
        }
        csv_rows.append({
            "model_family": name,
            "architecture_type": arch_type,
            "parameter_count": param_count,
            "single_sample_latency_mean_ms": round(single_res["mean_latency_ms"], 4),
            "single_sample_latency_std_ms": round(single_res["std_latency_ms"], 4),
            "single_sample_latency_p50_ms": round(single_res["p50_latency_ms"], 4),
            "single_sample_latency_p95_ms": round(single_res["p95_latency_ms"], 4),
            "batch_latency_mean_ms": round(batch_res["mean_latency_ms"], 4),
            "batch_latency_std_ms": round(batch_res["std_latency_ms"], 4),
            "sustained_throughput_samples_per_sec": round(batch_res["throughput_samples_per_sec"], 2),
            "peak_rss_mb": round(batch_res["peak_rss_mb"], 2),
            "device": "cpu",
        })

    return family_results, csv_rows


def execute_reproducibility_audit(
    root: Path,
    runs_dir: Path,
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    """Execute end-to-end replay verification and traceability audit."""
    cohort_path = root / "data/cohort.csv"
    src_path = root / "data/source_records.csv"

    run_dirs = sorted(p for p in runs_dir.iterdir() if p.is_dir())
    run_audits: list[dict[str, Any]] = []

    # Benchmark replays across all discovered runs
    for rd in run_dirs:
        attempt_dir = rd / "attempt0001"
        if not attempt_dir.is_dir():
            continue

        exp_id = rd.name
        # Parse seed: exp_{family}_s{seed} or exp_{family}_replay_s{seed}
        clean_parts = exp_id.split("_s")
        seed = int(clean_parts[-1]) if len(clean_parts) > 1 and clean_parts[-1].isdigit() else 42

        # Direct prediction check against recorded attempt
        pred_file = attempt_dir / "predictions.csv"
        if not pred_file.is_file():
            continue

        # Execute isolated replay audit
        audit_res = audit_run_replay(
            attempt_dir,
            cohort_path,
            src_path,
            seed=seed,
            experiment_id=exp_id,
            tolerance=tolerance,
        )
        run_audits.append(audit_res)

    all_within_tol = all(r["within_tolerance"] for r in run_audits)
    all_bitwise = all(r["bitwise_identical"] for r in run_audits)
    max_observed_error = float(max(r["max_absolute_error"] for r in run_audits)) if run_audits else 0.0

    # Traceability Audit: Verify figures_data.json matches statistical_summary.json
    traceability_status = "PASS"
    traceability_errors = []
    fig_path = root / "project/figures_data.json"
    stat_path = root / "project/statistical_summary.json"

    if fig_path.is_file() and stat_path.is_file():
        fig_data = json.loads(fig_path.read_text(encoding="utf-8"))
        stat_data = json.loads(stat_path.read_text(encoding="utf-8"))

        fam_stat = stat_data.get("family_aggregates", {})
        cal_fig = fig_data.get("calibration_curves", {})

        for fam, cdata in cal_fig.items():
            if fam not in fam_stat:
                traceability_errors.append(f"Family '{fam}' in figures_data not found in statistical_summary")
                continue
            stat_ece = fam_stat[fam]["expected_calibration_error"]["mean"]
            fig_ece = cdata["ece"]
            if abs(stat_ece - fig_ece) > 1e-9:
                traceability_errors.append(f"ECE mismatch for {fam}: {fig_ece} != {stat_ece}")

        if traceability_errors:
            traceability_status = "FAIL"

    return {
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "tolerance": tolerance,
        "n_runs_audited": len(run_audits),
        "all_within_tolerance": all_within_tol,
        "all_bitwise_identical": all_bitwise,
        "max_observed_error": max_observed_error,
        "traceability_audit": {
            "status": traceability_status,
            "discrepancies": traceability_errors,
        },
        "overall_status": "PASS" if (all_within_tol and traceability_status == "PASS") else "FAIL",
        "runs": run_audits,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Hardware measurement and reproducibility audit")
    parser.add_argument("--root", default=".", help="Project root directory")
    parser.add_argument("--runs-dir", default=None, help="Directory containing experiment runs")
    parser.add_argument("--trials", type=int, default=50, help="Number of benchmark trials")
    parser.add_argument("--warmup", type=int, default=10, help="Number of warmup trials")
    parser.add_argument("--tolerance", type=float, default=1e-6, help="Replay numerical tolerance")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    runs_dir = find_latest_runs_dir(root, args.runs_dir)
    out_dir = root / "project"

    print(f"Executing hardware validation on {root}...")
    hw_info = get_host_hardware_info()
    print(f"Host: {hw_info['cpu_model']} ({hw_info['architecture']}), PyTorch {hw_info['torch_version']} ({hw_info['device']})")

    # 1. Benchmarking
    print("\n[1/2] Benchmarking sustained inference latency and throughput...")
    benchmarks, csv_rows = benchmark_all_model_families(
        root, runs_dir, measured_trials=args.trials, warmup_trials=args.warmup
    )

    hw_payload = {
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "host_hardware": hw_info,
        "models": benchmarks,
    }
    (out_dir / "hardware_metrics.json").write_text(json.dumps(hw_payload, indent=2), encoding="utf-8")

    # Write CSV
    if csv_rows:
        fieldnames = list(csv_rows[0].keys())
        with (out_dir / "hardware_summary.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(csv_rows)

    print("Completed hardware benchmark:")
    print(f"{'Model Family':<26} | {'Params':<8} | {'Single Lat (ms)':<16} | {'Batch Lat (ms)':<16} | {'Throughput (samp/s)':<20} | {'Peak RSS':<10}")
    print("-" * 105)
    for r in csv_rows:
        s_lat = f"{r['single_sample_latency_mean_ms']:.3f}±{r['single_sample_latency_std_ms']:.3f}"
        b_lat = f"{r['batch_latency_mean_ms']:.3f}±{r['batch_latency_std_ms']:.3f}"
        print(f"{r['model_family']:<26} | {r['parameter_count']:<8} | {s_lat:<16} | {b_lat:<16} | {r['sustained_throughput_samples_per_sec']:<20} | {r['peak_rss_mb']:.1f} MB")

    # 2. Reproducibility & Traceability Audit
    print("\n[2/2] Auditing end-to-end clean replay reproducibility and artifact traceability...")
    replay_res = execute_reproducibility_audit(root, runs_dir, tolerance=args.tolerance)
    (out_dir / "reproducibility_audit.json").write_text(json.dumps(replay_res, indent=2), encoding="utf-8")

    print(f"Replay Audit Result: {replay_res['overall_status']}")
    print(f"Runs Audited: {replay_res['n_runs_audited']}")
    print(f"All within tolerance (|Δ| < {args.tolerance}): {replay_res['all_within_tolerance']}")
    print(f"Max observed error: {replay_res['max_observed_error']:.2e}")
    print(f"Traceability status: {replay_res['traceability_audit']['status']}")

    return 0 if replay_res["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
