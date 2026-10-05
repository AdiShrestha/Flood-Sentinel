"""Pilot training, comparator ladder implementations, and hardware resource measurement."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import math
import os
import resource
import time
from typing import Any, Mapping, Sequence

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from .baselines import ewma_cusum, persistence_forecast, rate_of_change
from .dataset import CausalHydroDataset, CausalHydroSample, collate_causal_batch, create_dataloader
from .ea_lstm import EALSTMModel
from .reconstruction import (
    MaskedHydroModel,
    compute_score_a,
    compute_score_b,
    fit_latent_reference,
    sample_corruption_mask,
)
from .scaler import PersistentScaler


# =========================================================================
# Hardware Resource Profiler
# =========================================================================

@dataclass(frozen=True)
class HardwareProfile:
    """Empirical hardware measurement receipt."""
    device: str
    wall_clock_seconds: float
    peak_rss_mb: float
    sample_count: int
    throughput_samples_per_sec: float
    total_parameters: int
    trainable_parameters: int


def measure_hardware_profile(
    start_time: float,
    sample_count: int,
    model: nn.Module | None = None,
    device: str = "cpu",
) -> HardwareProfile:
    """Measure elapsed execution time, peak memory usage, and throughput."""
    elapsed = max(time.perf_counter() - start_time, 1e-6)
    rusage = resource.getrusage(resource.RUSAGE_SELF)
    # On macOS, ru_maxrss is in bytes; on Linux, it is in kilobytes.
    import platform
    if platform.system() == "Darwin":
        peak_rss_mb = rusage.ru_maxrss / (1024.0 * 1024.0)
    else:
        peak_rss_mb = rusage.ru_maxrss / 1024.0

    total_params = 0
    trainable_params = 0
    if model is not None:
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

    throughput = sample_count / elapsed

    return HardwareProfile(
        device=device,
        wall_clock_seconds=float(elapsed),
        peak_rss_mb=float(peak_rss_mb),
        sample_count=sample_count,
        throughput_samples_per_sec=float(throughput),
        total_parameters=total_params,
        trainable_parameters=trainable_params,
    )


# =========================================================================
# Tier 1: True Persistence Comparator
# =========================================================================

class PersistenceComparator:
    """Evaluates persistence warning based purely on latest observed stage and velocity."""

    @staticmethod
    def evaluate_sample(sample: CausalHydroSample, stage_channel_idx: int = 0) -> float:
        """Extract latest observed stage value as the baseline score."""
        vals = sample.values[:, stage_channel_idx].numpy()
        obs = sample.observed[:, stage_channel_idx].numpy()
        observed_indices = np.where(obs)[0]
        if len(observed_indices) == 0:
            return 0.0
        latest_idx = observed_indices[-1]
        latest_val = float(vals[latest_idx])
        # Persistence score is normalized latest stage
        return latest_val

    @classmethod
    def evaluate_dataset(cls, dataset: CausalHydroDataset) -> list[float]:
        return [cls.evaluate_sample(dataset[i]) for i in range(len(dataset))]


# =========================================================================
# Tier 2: Continuous EWMA-CUSUM Comparator
# =========================================================================

class EWMACUSUMComparator:
    """Statistical process control baseline running EWMA-CUSUM on standardized stage."""

    def __init__(
        self,
        calibration_mean: float = 0.0,
        calibration_scale: float = 1.0,
        alpha: float = 0.2,
        slack: float = 0.5,
    ) -> None:
        self.mean = calibration_mean
        self.scale = max(calibration_scale, 1e-6)
        self.alpha = alpha
        self.slack = slack

    @classmethod
    def fit_from_dataset(
        cls,
        train_dataset: CausalHydroDataset,
        stage_channel_idx: int = 0,
        alpha: float = 0.2,
        slack: float = 0.5,
    ) -> EWMACUSUMComparator:
        """Fit calibration mean and scale strictly on train observations."""
        all_stage_obs: list[float] = []
        for i in range(len(train_dataset)):
            s = train_dataset[i]
            vals = s.values[:, stage_channel_idx].numpy()
            obs = s.observed[:, stage_channel_idx].numpy()
            all_stage_obs.extend(vals[obs].tolist())

        if not all_stage_obs:
            raise ValueError("No observed training stage records found for EWMA-CUSUM.")

        mean_v = float(np.mean(all_stage_obs))
        scale_v = float(np.std(all_stage_obs))
        if scale_v <= 0:
            scale_v = 1.0

        return cls(calibration_mean=mean_v, calibration_scale=scale_v, alpha=alpha, slack=slack)

    def evaluate_sample(self, sample: CausalHydroSample, stage_channel_idx: int = 0) -> float:
        """Run EWMA-CUSUM across the 24h lookback sequence, returning the terminal CUSUM score."""
        vals = sample.values[:, stage_channel_idx].numpy()
        obs = sample.observed[:, stage_channel_idx].numpy()
        # For gaps, forward fill the last observed value
        series = np.array(vals)
        last_v = self.mean
        for t in range(len(series)):
            if obs[t]:
                last_v = series[t]
            else:
                series[t] = last_v

        scores, state = ewma_cusum(
            series,
            calibration_mean=self.mean,
            calibration_scale=self.scale,
            alpha=self.alpha,
            slack=self.slack,
            initial_ewma=float(series[0]),
            initial_cusum=0.0,
        )
        return float(state["cusum"])

    def evaluate_dataset(self, dataset: CausalHydroDataset) -> list[float]:
        return [self.evaluate_sample(dataset[i]) for i in range(len(dataset))]


# =========================================================================
# Tier 3: Tabular Ridge Logistic Comparator
# =========================================================================

class TabularRidgeComparator:
    """Linear statistical baseline on 24h summary statistics."""

    def __init__(self, l2_reg: float = 1.0) -> None:
        self.l2_reg = l2_reg
        self.weights: np.ndarray | None = None
        self.bias: float = 0.0
        self.feature_names: list[str] = [
            "stage_mean", "stage_std", "stage_min", "stage_max", "stage_latest", "stage_delta",
            "flow_mean", "flow_std", "flow_latest", "flow_delta",
        ]

    @staticmethod
    def extract_features(sample: CausalHydroSample) -> np.ndarray:
        """Extract a 10-dimensional causal relative dynamic feature vector from a 24h lookback sequence."""
        feats: list[float] = []
        for ch in [0, 1]:  # 0: stage, 1: discharge
            if ch < sample.values.shape[1]:
                vals = sample.values[:, ch].numpy()
                obs = sample.observed[:, ch].numpy()
                observed_vals = vals[obs]
                if len(observed_vals) > 1:
                    base = observed_vals[0]
                    feats.append(float(observed_vals[-1] - base))       # delta
                    feats.append(float(np.std(observed_vals)))          # std
                    if ch == 0:
                        feats.append(float(np.min(observed_vals) - base))   # min rel
                        feats.append(float(np.max(observed_vals) - base))   # max rel
                    feats.append(float(np.max(observed_vals) - np.min(observed_vals))) # range
                    feats.append(float(observed_vals[-1] - np.mean(observed_vals)))    # diff from mean
                else:
                    feats.extend([0.0] * (6 if ch == 0 else 4))
            else:
                feats.extend([0.0] * (6 if ch == 0 else 4))
        return np.array(feats, dtype=np.float64)

    def fit(self, train_dataset: CausalHydroDataset) -> None:
        """Fit L2-regularized logistic regression strictly on training samples."""
        X_list: list[np.ndarray] = []
        y_list: list[int] = []
        for i in range(len(train_dataset)):
            s = train_dataset[i]
            X_list.append(self.extract_features(s))
            y_list.append(s.label)

        X = np.stack(X_list, axis=0)  # (N, D)
        y = np.array(y_list, dtype=np.float64)  # (N,)

        N, D = X.shape
        w = np.zeros(D, dtype=np.float64)
        b = 0.0
        lr = 0.05
        for _ in range(300):
            logits = np.dot(X, w) + b
            probs = 1.0 / (1.0 + np.exp(-np.clip(logits, -20.0, 20.0)))
            grad_w = np.dot(X.T, (probs - y)) / N + self.l2_reg * w
            grad_b = float(np.mean(probs - y))
            w -= lr * grad_w
            b -= lr * grad_b

        self.weights = w
        self.bias = b

    def predict_proba(self, sample: CausalHydroSample) -> float:
        """Predict probability of future flood precursor."""
        if self.weights is None:
            raise ValueError("TabularRidgeComparator must be fitted before predict_proba.")
        x = self.extract_features(sample)
        logit = float(np.dot(x, self.weights) + self.bias)
        p = 1.0 / (1.0 + math.exp(-max(min(logit, 20.0), -20.0)))
        return float(max(min(p, 1.0 - 1e-6), 1e-6))

    def evaluate_dataset(self, dataset: CausalHydroDataset) -> list[float]:
        return [self.predict_proba(dataset[i]) for i in range(len(dataset))]


# =========================================================================
# Tier 4: Supervised EA-LSTM Pilot Trainer
# =========================================================================

@dataclass(frozen=True)
class TrainingTrace:
    epoch: int
    train_loss: float
    val_loss: float
    val_auroc: float | None = None


class EALSTMPilotTrainer:
    """Supervised recurrent neural baseline pilot trainer."""

    def __init__(
        self,
        dynamic_dim: int = 2,
        static_dim: int = 4,
        hidden_dim: int = 16,
        lr: float = 1e-3,
        weight_decay: float = 1e-4,
    ) -> None:
        self.model = EALSTMModel(
            dynamic_dim=dynamic_dim,
            static_dim=static_dim,
            hidden_dim=hidden_dim,
            classifier_width=8,
            dropout=0.0,
        )
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(), lr=lr, weight_decay=weight_decay
        )
        self.criterion = nn.BCEWithLogitsLoss()
        self.static_dim = static_dim

    def _get_static_features(self, sample_ids: Sequence[str]) -> torch.Tensor:
        """Construct deterministic static catchment embedding from site number."""
        static = torch.zeros((len(sample_ids), self.static_dim), dtype=torch.float32)
        for i, sid in enumerate(sample_ids):
            # One-hot encoding of known basins
            if "01646500" in sid:
                static[i, 0] = 1.0
            elif "01463500" in sid:
                static[i, 1] = 1.0
            elif "01434000" in sid:
                static[i, 2] = 1.0
            else:
                static[i, 3] = 1.0
        return static

    def train_pilot(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        max_epochs: int = 10,
        patience: int = 3,
        min_delta: float = 1e-4,
    ) -> tuple[list[TrainingTrace], dict[str, Any], HardwareProfile]:
        """Train EA-LSTM pilot with early stopping on validation loss."""
        start_time = time.perf_counter()
        traces: list[TrainingTrace] = []
        best_val_loss = float("inf")
        best_epoch = 1
        best_state: dict[str, Any] = {}
        patience_counter = 0
        total_samples = 0

        for epoch in range(1, max_epochs + 1):
            self.model.train()
            train_losses: list[float] = []
            for batch in train_loader:
                x_dyn = batch["values"] - batch["values"][:, :1, :]
                labels = batch["labels"].float()
                x_static = self._get_static_features(batch["sample_ids"])
                total_samples += len(labels)

                self.optimizer.zero_grad()
                logits = self.model(x_dyn, x_static)
                loss = self.criterion(logits, labels)
                loss.backward()
                self.optimizer.step()
                train_losses.append(loss.item())

            avg_train_loss = float(np.mean(train_losses))

            # Validation
            self.model.eval()
            val_losses: list[float] = []
            with torch.no_grad():
                for batch in val_loader:
                    x_dyn = batch["values"] - batch["values"][:, :1, :]
                    labels = batch["labels"].float()
                    x_static = self._get_static_features(batch["sample_ids"])
                    logits = self.model(x_dyn, x_static)
                    val_losses.append(self.criterion(logits, labels).item())

            avg_val_loss = float(np.mean(val_losses))
            traces.append(TrainingTrace(epoch=epoch, train_loss=avg_train_loss, val_loss=avg_val_loss))

            # Early stopping check
            if avg_val_loss < (best_val_loss - min_delta):
                best_val_loss = avg_val_loss
                best_epoch = epoch
                best_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
                patience_counter = 0
            else:
                patience_counter += 1
                if epoch >= 2 and patience_counter >= patience:
                    break

        # Load best checkpoint
        if best_state:
            self.model.load_state_dict(best_state)

        profile = measure_hardware_profile(start_time, total_samples, self.model)
        checkpoint_meta = {
            "best_epoch": best_epoch,
            "best_val_loss": best_val_loss,
            "total_epochs": len(traces),
        }
        return traces, checkpoint_meta, profile

    def evaluate_dataset(self, loader: DataLoader) -> list[float]:
        self.model.eval()
        scores: list[float] = []
        with torch.no_grad():
            for batch in loader:
                x_dyn = batch["values"] - batch["values"][:, :1, :]
                x_static = self._get_static_features(batch["sample_ids"])
                logits = self.model(x_dyn, x_static)
                probs = torch.sigmoid(logits).tolist()
                scores.extend(probs)
        return scores


# =========================================================================
# Tiers 5 & 6: Proposed Masked Hydro Pilot Trainer
# =========================================================================

class MaskedHydroPilotTrainer:
    """Self-supervised Masked Hydro Foundation Model pilot trainer."""

    def __init__(
        self,
        in_channels: int = 2,
        d_model: int = 16,
        tcn_layers: int = 1,
        transformer_layers: int = 1,
        n_heads: int = 2,
        lr: float = 1e-3,
        weight_decay: float = 1e-4,
    ) -> None:
        self.model = MaskedHydroModel(
            physical_channels=in_channels,
            d_model=d_model,
            tcn_layers=tcn_layers,
            transformer_layers=transformer_layers,
            n_heads=n_heads,
            d_ff=32,
            dropout=0.0,
        )
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(), lr=lr, weight_decay=weight_decay
        )

    def train_pilot(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        max_epochs: int = 10,
        patience: int = 3,
        min_delta: float = 1e-4,
        corruption_rate: float = 0.25,
    ) -> tuple[list[TrainingTrace], dict[str, Any], HardwareProfile]:
        """Train self-supervised Masked Hydro Model on masked reconstruction loss."""
        start_time = time.perf_counter()
        traces: list[TrainingTrace] = []
        best_val_loss = float("inf")
        best_epoch = 1
        best_state: dict[str, Any] = {}
        patience_counter = 0
        total_samples = 0

        for epoch in range(1, max_epochs + 1):
            self.model.train()
            train_losses: list[float] = []
            for batch in train_loader:
                vals = batch["values"]
                obs = batch["observed"]
                total_samples += len(vals)

                hidden = sample_corruption_mask(
                    obs, mode="random", rate=corruption_rate, seed=epoch * 1000
                )
                self.optimizer.zero_grad()
                loss = self.model.masked_loss(vals, obs, hidden)
                loss.backward()
                self.optimizer.step()
                train_losses.append(loss.item())

            avg_train_loss = float(np.mean(train_losses))

            # Validation masked loss
            self.model.eval()
            val_losses: list[float] = []
            with torch.no_grad():
                for batch in val_loader:
                    vals = batch["values"]
                    obs = batch["observed"]
                    hidden = sample_corruption_mask(
                        obs, mode="random", rate=corruption_rate, seed=42
                    )
                    loss = self.model.masked_loss(vals, obs, hidden)
                    val_losses.append(loss.item())

            avg_val_loss = float(np.mean(val_losses))
            traces.append(TrainingTrace(epoch=epoch, train_loss=avg_train_loss, val_loss=avg_val_loss))

            # Early stopping check
            if avg_val_loss < (best_val_loss - min_delta):
                best_val_loss = avg_val_loss
                best_epoch = epoch
                best_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
                patience_counter = 0
            else:
                patience_counter += 1
                if epoch >= 2 and patience_counter >= patience:
                    break

        if best_state:
            self.model.load_state_dict(best_state)

        profile = measure_hardware_profile(start_time, total_samples, self.model)
        checkpoint_meta = {
            "best_epoch": best_epoch,
            "best_val_loss": best_val_loss,
            "total_epochs": len(traces),
        }
        return traces, checkpoint_meta, profile

    def evaluate_score_a(self, loader: DataLoader) -> list[float]:
        """Extract Score A (leave-channel-out masked residual MSE)."""
        self.model.eval()
        scores: list[float] = []
        with torch.no_grad():
            for batch in loader:
                sc = compute_score_a(
                    self.model,
                    batch["values"],
                    batch["observed"],
                    aggregation="mean",
                    allow_missing_steps=True,
                )
                scores.extend(sc.tolist())
        return scores

    def evaluate_score_b(self, train_loader: DataLoader, eval_loader: DataLoader) -> list[float]:
        """Extract Score B (latent space Mahalanobis distance relative to train covariance)."""
        self.model.eval()
        ref = fit_latent_reference(self.model, train_loader, split="train", shrinkage=0.1)
        scores: list[float] = []
        with torch.no_grad():
            for batch in eval_loader:
                sc = compute_score_b(self.model, batch["values"], batch["observed"], ref)
                scores.extend(sc.tolist())
        return scores
