#!/usr/bin/env python3
"""Standardized experiment runner executed under supervisor contracts.

Dispatches execution based on experiment_id to the appropriate comparator
or neural model, ensuring deterministic seed initialization, train-only
scaling, early stopping, and metric calculation on declared evaluation splits.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Any

# Ensure source is on sys.path
SOURCE_DIR = Path(__file__).resolve().parents[1]
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader

from flood_sentinel.adapters.recompute import recompute_binary_metrics
from flood_sentinel.dataset import CausalHydroDataset, create_dataloader
from flood_sentinel.model import CausalForecastingHead, CausalHydroEncoder
from flood_sentinel.pilots import (
    EALSTMPilotTrainer,
    EWMACUSUMComparator,
    MaskedHydroPilotTrainer,
    PersistenceComparator,
    TabularRidgeComparator,
)
from flood_sentinel.reconstruction import (
    compute_score_a,
    compute_score_b,
    fit_latent_reference,
)
from flood_sentinel.scaler import PersistentScaler


class TrainPlattCalibrator:
    """Univariate logistic calibrator fitted strictly on training scores and labels.

    Preserves rank order via monotonically non-decreasing parameter constraints,
    mapping unbounded anomaly or physical velocities to well-defined probabilities in (0, 1).
    """

    def __init__(self, l2_reg: float = 0.1, max_iter: int = 200, lr: float = 0.05) -> None:
        self.w = 1.0
        self.b = 0.0
        self.l2_reg = l2_reg
        self.max_iter = max_iter
        self.lr = lr

    def fit(self, scores: list[float], labels: list[int]) -> TrainPlattCalibrator:
        s = np.array(scores, dtype=np.float64)
        y = np.array(labels, dtype=np.float64)
        w, b = 1.0, 0.0
        for _ in range(self.max_iter):
            logits = np.clip(w * s + b, -20.0, 20.0)
            p = 1.0 / (1.0 + np.exp(-logits))
            grad_w = np.mean((p - y) * s) + self.l2_reg * w
            grad_b = np.mean(p - y)
            w -= self.lr * grad_w
            b -= self.lr * grad_b
            if w < 0.01:
                w = 0.01
        self.w = float(w)
        self.b = float(b)
        return self

    def predict(self, scores: list[float]) -> list[float]:
        s = np.array(scores, dtype=np.float64)
        logits = np.clip(self.w * s + self.b, -20.0, 20.0)
        p = 1.0 / (1.0 + np.exp(-logits))
        return np.clip(p, 1e-6, 1.0 - 1e-6).tolist()


def parse_model_family(experiment_id: str) -> str:
    """Extract model family name from experiment_id."""
    for family in [
        "persistence",
        "ewma_cusum",
        "tabular_ridge",
        "ea_lstm",
        "masked_hydro_score_a",
        "masked_hydro_score_b",
        "causal_forecasting_head",
    ]:
        if family in experiment_id:
            return family
    raise ValueError(f"Cannot identify model family from experiment_id '{experiment_id}'")


def train_forecasting_pilot(
    train_loader: DataLoader,
    val_loader: DataLoader,
    seed: int,
    run_dir: Path,
    max_epochs: int = 60,
    patience: int = 3,
    min_delta: float = 0.01,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Train CausalForecastingHead on top of CausalHydroEncoder with early stopping."""
    torch.manual_seed(seed)
    encoder = CausalHydroEncoder(
        in_channels=4,
        d_model=16,
        tcn_layers=1,
        transformer_layers=1,
        n_heads=2,
        d_ff=32,
        dropout=0.0,
    )
    head = CausalForecastingHead(d_model=16, out_dim=1)

    initial_ckpt = run_dir / "initial_checkpoint.pt"
    torch.save({"encoder": encoder.state_dict(), "head": head.state_dict()}, initial_ckpt)

    optimizer = torch.optim.Adam(list(encoder.parameters()) + list(head.parameters()), lr=5e-3, weight_decay=1e-3)
    criterion = nn.BCEWithLogitsLoss()

    best_loss = float("inf")
    best_epoch = 1
    best_state: dict[str, Any] = {}
    no_improve = 0
    traces = []

    for epoch in range(1, max_epochs + 1):
        encoder.train()
        head.train()
        train_losses = []
        for batch in train_loader:
            v = batch["values"]
            o = batch["observed"]
            y = batch["labels"].float().unsqueeze(-1)
            v_rel = v - v[:, :1, :]
            inp = torch.cat((v_rel, o.float()), dim=-1)
            optimizer.zero_grad()
            z = encoder(inp)
            pred = head(z)
            loss = criterion(pred, y)
            loss.backward()
            optimizer.step()
            train_losses.append(loss.item())
        avg_train = float(np.mean(train_losses))

        encoder.eval()
        head.eval()
        val_losses = []
        with torch.no_grad():
            for batch in val_loader:
                v = batch["values"]
                o = batch["observed"]
                y = batch["labels"].float().unsqueeze(-1)
                v_rel = v - v[:, :1, :]
                inp = torch.cat((v_rel, o.float()), dim=-1)
                z = encoder(inp)
                pred = head(z)
                loss = criterion(pred, y)
                val_losses.append(loss.item())
        avg_val = float(np.mean(val_losses))
        traces.append({"epoch": epoch, "train_loss": avg_train, "validation_loss": avg_val})

        if avg_val < best_loss - min_delta:
            best_loss = avg_val
            best_epoch = epoch
            best_state = {"encoder": encoder.state_dict(), "head": head.state_dict()}
            no_improve = 0
        else:
            no_improve += 1
            if no_improve >= patience and epoch >= 2:
                break

    best_ckpt = run_dir / "checkpoint.pt"
    torch.save(best_state or {"encoder": encoder.state_dict(), "head": head.state_dict()}, best_ckpt)
    if best_state:
        encoder.load_state_dict(best_state["encoder"])
        head.load_state_dict(best_state["head"])

    meta = {
        "best_epoch": best_epoch,
        "best_val_loss": best_loss,
        "epochs_trained": len(traces),
        "model": (encoder, head),
    }
    return meta, traces


def run_experiment(run_dir: Path, seed: int, experiment_id: str) -> None:
    run_dir = Path(run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    torch.manual_seed(seed)
    np.random.seed(seed)

    root = Path.cwd()
    cohort_path = root / "data/cohort.csv"
    src_path = root / "data/source_records.csv"

    family = parse_model_family(experiment_id)

    # 1. Dataset Loading & Train-Only Normalization
    train_ds_raw = CausalHydroDataset(cohort_path, src_path, split="train")
    raw_train = train_ds_raw.get_raw_observations_matrix()
    scaler = PersistentScaler.fit(raw_train, train_ds_raw.channels, split="train")

    train_ds = CausalHydroDataset(cohort_path, src_path, split="train", scaler=scaler)
    val_ds = CausalHydroDataset(cohort_path, src_path, split="validation", scaler=scaler)
    test_ds = CausalHydroDataset(cohort_path, src_path, split="test", scaler=scaler)

    train_loader = create_dataloader(train_ds, batch_size=2, shuffle=True)
    val_loader = create_dataloader(val_ds, batch_size=2, shuffle=False)
    test_loader = create_dataloader(test_ds, batch_size=2, shuffle=False)

    train_labels = [train_ds[i].label for i in range(len(train_ds))]
    val_labels = [val_ds[i].label for i in range(len(val_ds))]
    test_labels = [test_ds[i].label for i in range(len(test_ds))]

    is_deterministic = family in ("persistence", "ewma_cusum", "tabular_ridge")
    result_meta: dict[str, Any] = {}

    # 2. Model Training / Evaluation
    if family == "persistence":
        train_raw = PersistenceComparator.evaluate_dataset(train_ds)
        val_raw = PersistenceComparator.evaluate_dataset(val_ds)
        test_raw = PersistenceComparator.evaluate_dataset(test_ds)
        calibrator = TrainPlattCalibrator().fit(train_raw, train_labels)
        val_preds = calibrator.predict(val_raw)
        test_preds = calibrator.predict(test_raw)
        (run_dir / "method.txt").write_text("Tier 1 Persistence baseline: stage velocity forward projection with Platt probability mapping.\n")

    elif family == "ewma_cusum":
        cusum = EWMACUSUMComparator.fit_from_dataset(train_ds)
        train_raw = cusum.evaluate_dataset(train_ds)
        val_raw = cusum.evaluate_dataset(val_ds)
        test_raw = cusum.evaluate_dataset(test_ds)
        calibrator = TrainPlattCalibrator().fit(train_raw, train_labels)
        val_preds = calibrator.predict(val_raw)
        test_preds = calibrator.predict(test_raw)
        (run_dir / "method.txt").write_text("Tier 2 EWMA-CUSUM baseline: statistical process control with Platt probability mapping.\n")

    elif family == "tabular_ridge":
        ridge = TabularRidgeComparator(l2_reg=1.0)
        ridge.fit(train_ds)
        val_preds = ridge.evaluate_dataset(val_ds)
        test_preds = ridge.evaluate_dataset(test_ds)
        (run_dir / "method.txt").write_text("Tier 3 Tabular Ridge baseline: L2-regularized logistic regression.\n")

    elif family == "ea_lstm":
        ea_trainer = EALSTMPilotTrainer(dynamic_dim=2, static_dim=4, hidden_dim=16, lr=1e-2, weight_decay=1e-2)
        torch.save(ea_trainer.model.state_dict(), run_dir / "initial_checkpoint.pt")
        traces, meta, _ = ea_trainer.train_pilot(
            train_loader, val_loader, max_epochs=60, patience=3, min_delta=0.01
        )
        torch.save(ea_trainer.model.state_dict(), run_dir / "checkpoint.pt")
        with (run_dir / "history.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["epoch", "train_loss", "validation_loss"])
            w.writeheader()
            for t in traces:
                w.writerow({"epoch": t.epoch, "train_loss": t.train_loss, "validation_loss": t.val_loss})

        val_preds = ea_trainer.evaluate_dataset(val_loader)
        test_preds = ea_trainer.evaluate_dataset(test_loader)
        result_meta["history"] = "history.csv"
        result_meta["epochs_trained"] = meta["total_epochs"]
        result_meta["checkpoint_epoch"] = meta["best_epoch"]
        result_meta["checkpoint"] = "checkpoint.pt"
        result_meta["initial_checkpoint"] = "initial_checkpoint.pt"

    elif family == "masked_hydro_score_a":
        mh_trainer = MaskedHydroPilotTrainer(
            in_channels=2, d_model=16, lr=1e-3
        )
        torch.save(mh_trainer.model.state_dict(), run_dir / "initial_checkpoint.pt")
        traces, meta, _ = mh_trainer.train_pilot(
            train_loader, val_loader, max_epochs=60, patience=3, min_delta=0.2
        )
        torch.save(mh_trainer.model.state_dict(), run_dir / "checkpoint.pt")
        with (run_dir / "history.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["epoch", "train_loss", "validation_loss"])
            w.writeheader()
            for t in traces:
                w.writerow({"epoch": t.epoch, "train_loss": t.train_loss, "validation_loss": t.val_loss})

        train_raw = mh_trainer.evaluate_score_a(train_loader)
        val_raw = mh_trainer.evaluate_score_a(val_loader)
        test_raw = mh_trainer.evaluate_score_a(test_loader)
        calibrator = TrainPlattCalibrator().fit(train_raw, train_labels)
        val_preds = calibrator.predict(val_raw)
        test_preds = calibrator.predict(test_raw)
        result_meta["history"] = "history.csv"
        result_meta["epochs_trained"] = meta["total_epochs"]
        result_meta["checkpoint_epoch"] = meta["best_epoch"]
        result_meta["checkpoint"] = "checkpoint.pt"
        result_meta["initial_checkpoint"] = "initial_checkpoint.pt"

    elif family == "masked_hydro_score_b":
        mh_trainer = MaskedHydroPilotTrainer(
            in_channels=2, d_model=16, lr=1e-3
        )
        torch.save(mh_trainer.model.state_dict(), run_dir / "initial_checkpoint.pt")
        traces, meta, _ = mh_trainer.train_pilot(
            train_loader, val_loader, max_epochs=60, patience=3, min_delta=0.2
        )
        torch.save(mh_trainer.model.state_dict(), run_dir / "checkpoint.pt")
        with (run_dir / "history.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["epoch", "train_loss", "validation_loss"])
            w.writeheader()
            for t in traces:
                w.writerow({"epoch": t.epoch, "train_loss": t.train_loss, "validation_loss": t.val_loss})

        train_raw = mh_trainer.evaluate_score_b(train_loader, train_loader)
        val_raw = mh_trainer.evaluate_score_b(train_loader, val_loader)
        test_raw = mh_trainer.evaluate_score_b(train_loader, test_loader)
        calibrator = TrainPlattCalibrator().fit(train_raw, train_labels)
        val_preds = calibrator.predict(val_raw)
        test_preds = calibrator.predict(test_raw)
        result_meta["history"] = "history.csv"
        result_meta["epochs_trained"] = meta["total_epochs"]
        result_meta["checkpoint_epoch"] = meta["best_epoch"]
        result_meta["checkpoint"] = "checkpoint.pt"
        result_meta["initial_checkpoint"] = "initial_checkpoint.pt"

    elif family == "causal_forecasting_head":
        meta, traces = train_forecasting_pilot(
            train_loader, val_loader, seed, run_dir, max_epochs=60, patience=3, min_delta=0.01
        )
        with (run_dir / "history.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["epoch", "train_loss", "validation_loss"])
            w.writeheader()
            w.writerows(traces)

        encoder, head = meta["model"]
        encoder.eval()
        head.eval()

        def predict_loader(loader: DataLoader) -> list[float]:
            scores = []
            with torch.no_grad():
                for batch in loader:
                    v = batch["values"]
                    o = batch["observed"]
                    v_rel = v - v[:, :1, :]
                    inp = torch.cat((v_rel, o.float()), dim=-1)
                    z = encoder(inp)
                    logits = head(z).squeeze(-1)
                    probs = torch.sigmoid(logits).tolist()
                    scores.extend(probs if isinstance(probs, list) else [probs])
            return [float(max(min(p, 1.0 - 1e-6), 1e-6)) for p in scores]

        val_preds = predict_loader(val_loader)
        test_preds = predict_loader(test_loader)
        result_meta["history"] = "history.csv"
        result_meta["epochs_trained"] = meta["epochs_trained"]
        result_meta["checkpoint_epoch"] = meta["best_epoch"]
        result_meta["checkpoint"] = "checkpoint.pt"
        result_meta["initial_checkpoint"] = "initial_checkpoint.pt"

    else:
        raise ValueError(f"Unknown family: {family}")

    # 3. Export predictions.csv (validation + test)
    pred_rows = []
    for i, s in enumerate(val_ds):
        pred_rows.append({"sample_id": s.sample_id, "label": str(s.label), "score": float(val_preds[i])})
    for i, s in enumerate(test_ds):
        pred_rows.append({"sample_id": s.sample_id, "label": str(s.label), "score": float(test_preds[i])})

    pred_file = run_dir / "predictions.csv"
    with pred_file.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["sample_id", "label", "score"])
        writer.writeheader()
        writer.writerows(pred_rows)

    # 4. Compute metrics
    val_metrics = recompute_binary_metrics(val_labels, val_preds, threshold=0.5)
    test_metrics = recompute_binary_metrics(test_labels, test_preds, threshold=0.5)

    result_payload: dict[str, Any] = {
        "experiment_id": experiment_id,
        "seed": seed,
        "config": {"family": family, "seed": seed},
        "predictions": "predictions.csv",
        "reported_metrics": {
            "validation": val_metrics,
            "test": test_metrics,
        },
    }

    if is_deterministic:
        result_payload["method_evidence"] = "method.txt"
    else:
        result_payload.update(result_meta)

    (run_dir / "result.json").write_text(json.dumps(result_payload, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Standardized experiment runner")
    parser.add_argument("--run-dir", dest="named_run_dir", default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--experiment-id", dest="named_exp_id", default=None)
    parser.add_argument("positional", nargs="*")

    args = parser.parse_args()

    run_dir = args.named_run_dir
    seed = args.seed
    exp_id = args.named_exp_id

    if args.positional:
        if run_dir is None and len(args.positional) >= 1:
            run_dir = args.positional[0]
        if seed is None and len(args.positional) >= 2:
            seed = int(args.positional[1])
        if exp_id is None and len(args.positional) >= 3:
            exp_id = args.positional[2]

    if run_dir is None:
        raise ValueError("Missing required run directory")
    if seed is None:
        seed = 42
    if exp_id is None:
        exp_id = "exp_persistence_s42"

    run_experiment(Path(run_dir), seed, exp_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
