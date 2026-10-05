"""Probability calibration curves, reliability diagrams, and Brier score decomposition.

Adheres strictly to Murphy (1973) exact Brier score partitioning and rigorous
statistical validation principles: zero holdout leakage, train-only calibration
fitting, and explicit sample support tracking.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import math
from typing import Any, Sequence

import numpy as np


@dataclass(frozen=True)
class CalibrationCurveResult:
    """Empirical reliability diagram and calibration error metrics."""
    bin_edges: list[float]
    bin_confs: list[float]
    bin_accs: list[float]
    bin_counts: list[int]
    expected_calibration_error: float
    maximum_calibration_error: float
    root_mean_squared_calibration_error: float
    n_samples: int
    strategy: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BrierDecompositionResult:
    """Murphy (1973) Brier score three-component decomposition: REL - RES + UNC."""
    brier_score_raw: float
    brier_score_binned: float
    reliability: float
    resolution: float
    uncertainty: float
    brier_skill_score: float
    algebraic_residual: float
    base_rate: float
    bin_counts: list[int]
    bin_forecasts: list[float]
    bin_observed: list[float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _validate_binary_inputs(
    y_true: Sequence[int | float],
    y_prob: Sequence[float],
) -> tuple[np.ndarray, np.ndarray]:
    """Validate aligned binary labels and probability vectors."""
    y = np.asarray(y_true, dtype=np.float64)
    p = np.asarray(y_prob, dtype=np.float64)
    if y.ndim != 1 or p.ndim != 1 or len(y) != len(p):
        raise ValueError("y_true and y_prob must be aligned 1D sequences of equal length.")
    if len(y) == 0:
        raise ValueError("Input sequences cannot be empty.")
    if not np.all(np.isin(y, [0.0, 1.0])):
        raise ValueError("y_true must contain only binary values {0, 1}.")
    if not np.all(np.isfinite(p)):
        raise ValueError("y_prob contains non-finite values.")
    if np.any(p < 0.0) or np.any(p > 1.0):
        raise ValueError(f"Probabilities must be bounded in [0, 1], got range [{p.min()}, {p.max()}].")
    return y, p


def compute_calibration_curve(
    y_true: Sequence[int | float],
    y_prob: Sequence[float],
    n_bins: int = 5,
    strategy: str = "uniform",
) -> CalibrationCurveResult:
    """Compute empirical calibration curve and calibration error statistics.

    Parameters:
        y_true: True binary targets in {0, 1}.
        y_prob: Forecast probabilities in [0, 1].
        n_bins: Number of probability discretization bins (default: 5).
        strategy: 'uniform' (equal width [0, 1]) or 'quantile' (equal sample count).

    Returns:
        CalibrationCurveResult containing bin statistics and ECE/MCE/RMSCE.
    """
    y, p = _validate_binary_inputs(y_true, y_prob)
    n = len(y)
    if n_bins < 2:
        raise ValueError(f"n_bins must be >= 2, got {n_bins}")

    if strategy == "uniform":
        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    elif strategy == "quantile":
        quantiles = np.linspace(0.0, 1.0, n_bins + 1)
        bin_edges = np.percentile(p, quantiles * 100.0)
        # Ensure strictly increasing edges to prevent zero-width quantile collapses
        for i in range(1, len(bin_edges)):
            if bin_edges[i] <= bin_edges[i - 1]:
                bin_edges[i] = bin_edges[i - 1] + 1e-6
    else:
        raise ValueError(f"strategy must be 'uniform' or 'quantile', got '{strategy}'")

    bin_indices = np.digitize(p, bin_edges[1:-1])  # 0 to n_bins - 1

    bin_confs: list[float] = []
    bin_accs: list[float] = []
    bin_counts: list[int] = []

    ece = 0.0
    mce = 0.0
    sum_sq_error = 0.0

    for b in range(n_bins):
        mask = (bin_indices == b)
        count = int(np.sum(mask))
        bin_counts.append(count)
        if count > 0:
            mean_conf = float(np.mean(p[mask]))
            mean_acc = float(np.mean(y[mask]))
            bin_confs.append(mean_conf)
            bin_accs.append(mean_acc)

            abs_err = abs(mean_acc - mean_conf)
            ece += (count / n) * abs_err
            mce = max(mce, abs_err)
            sum_sq_error += (count / n) * (abs_err ** 2)
        else:
            # Empty bin placeholder
            mid = float((bin_edges[b] + bin_edges[b + 1]) / 2.0)
            bin_confs.append(mid)
            bin_accs.append(0.0)

    rmsce = float(math.sqrt(sum_sq_error))

    return CalibrationCurveResult(
        bin_edges=bin_edges.tolist(),
        bin_confs=bin_confs,
        bin_accs=bin_accs,
        bin_counts=bin_counts,
        expected_calibration_error=float(ece),
        maximum_calibration_error=float(mce),
        root_mean_squared_calibration_error=rmsce,
        n_samples=n,
        strategy=strategy,
    )


def decompose_brier_score(
    y_true: Sequence[int | float],
    y_prob: Sequence[float],
    n_bins: int = 5,
    strategy: str = "uniform",
) -> BrierDecompositionResult:
    """Decompose Brier score into Murphy (1973) Reliability, Resolution, and Uncertainty.

    Mathematical Definition:
        BS_binned = Reliability - Resolution + Uncertainty
        - Uncertainty (UNC) = y_bar * (1 - y_bar)  [Climatological baseline variance]
        - Reliability (REL) = (1/N) * sum_k n_k * (p_bar_k - y_bar_k)^2  [Calibration error >= 0]
        - Resolution (RES)  = (1/N) * sum_k n_k * (y_bar_k - y_bar)^2  [Sorting power >= 0]
        - Brier Skill Score (BSS) = (RES - REL) / UNC

    Parameters:
        y_true: True binary targets in {0, 1}.
        y_prob: Forecast probabilities in [0, 1].
        n_bins: Number of probability discretization bins.
        strategy: 'uniform' or 'quantile'.

    Returns:
        BrierDecompositionResult validating algebraic consistency.
    """
    y, p = _validate_binary_inputs(y_true, y_prob)
    n = len(y)
    raw_brier = float(np.mean((p - y) ** 2))
    base_rate = float(np.mean(y))
    uncertainty = float(base_rate * (1.0 - base_rate))

    if strategy == "uniform":
        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    elif strategy == "quantile":
        quantiles = np.linspace(0.0, 1.0, n_bins + 1)
        bin_edges = np.percentile(p, quantiles * 100.0)
        for i in range(1, len(bin_edges)):
            if bin_edges[i] <= bin_edges[i - 1]:
                bin_edges[i] = bin_edges[i - 1] + 1e-6
    else:
        raise ValueError(f"strategy must be 'uniform' or 'quantile', got '{strategy}'")

    bin_indices = np.digitize(p, bin_edges[1:-1])

    bin_counts: list[int] = []
    bin_forecasts: list[float] = []
    bin_observed: list[float] = []

    reliability = 0.0
    resolution = 0.0
    binned_brier_sum = 0.0

    for b in range(n_bins):
        mask = (bin_indices == b)
        count = int(np.sum(mask))
        bin_counts.append(count)
        if count > 0:
            p_bar_k = float(np.mean(p[mask]))
            y_bar_k = float(np.mean(y[mask]))
            bin_forecasts.append(p_bar_k)
            bin_observed.append(y_bar_k)

            reliability += count * ((p_bar_k - y_bar_k) ** 2)
            resolution += count * ((y_bar_k - base_rate) ** 2)
            # Binned Brier term: sum_i (p_bar_k - y_i)^2
            binned_brier_sum += np.sum((p_bar_k - y[mask]) ** 2)
        else:
            bin_forecasts.append(float((bin_edges[b] + bin_edges[b + 1]) / 2.0))
            bin_observed.append(0.0)

    reliability /= n
    resolution /= n
    binned_brier = float(binned_brier_sum / n)

    theoretical_brier = reliability - resolution + uncertainty
    algebraic_residual = abs(binned_brier - theoretical_brier)

    bss = (resolution - reliability) / uncertainty if uncertainty > 0.0 else 0.0

    return BrierDecompositionResult(
        brier_score_raw=raw_brier,
        brier_score_binned=binned_brier,
        reliability=float(reliability),
        resolution=float(resolution),
        uncertainty=float(uncertainty),
        brier_skill_score=float(bss),
        algebraic_residual=float(algebraic_residual),
        base_rate=float(base_rate),
        bin_counts=bin_counts,
        bin_forecasts=bin_forecasts,
        bin_observed=bin_observed,
    )


class TrainPlattCalibrator:
    """Univariate logistic probability calibrator fitted strictly on training scores.

    Enforces non-negative slope constraint (w >= min_w) to guarantee exact
    rank-order preservation (AUROC and Average Precision invariance) while mapping
    continuous anomaly scores into calibrated probabilities in (0, 1).
    """

    def __init__(
        self,
        l2_reg: float = 0.1,
        max_iter: int = 200,
        lr: float = 0.05,
        min_w: float = 0.01,
    ) -> None:
        self.w = 1.0
        self.b = 0.0
        self.l2_reg = float(l2_reg)
        self.max_iter = int(max_iter)
        self.lr = float(lr)
        self.min_w = float(min_w)
        self._fitted = False

    def fit(self, scores: Sequence[float], labels: Sequence[int | float]) -> TrainPlattCalibrator:
        """Fit logistic scaling parameters strictly on training observations."""
        s = np.asarray(scores, dtype=np.float64)
        y = np.asarray(labels, dtype=np.float64)
        if len(s) != len(y) or len(s) == 0:
            raise ValueError("Scores and labels must be aligned non-empty sequences.")
        if not np.all(np.isin(y, [0.0, 1.0])):
            raise ValueError("Labels must be binary {0, 1}.")

        w, b = 1.0, 0.0
        for _ in range(self.max_iter):
            logits = np.clip(w * s + b, -25.0, 25.0)
            p = 1.0 / (1.0 + np.exp(-logits))
            grad_w = np.mean((p - y) * s) + self.l2_reg * w
            grad_b = np.mean(p - y)
            w -= self.lr * grad_w
            b -= self.lr * grad_b
            if w < self.min_w:
                w = self.min_w

        self.w = float(w)
        self.b = float(b)
        self._fitted = True
        return self

    def predict_proba(self, scores: Sequence[float], eps: float = 1e-6) -> list[float]:
        """Predict monotonic calibrated probabilities in [eps, 1 - eps]."""
        if not self._fitted:
            raise RuntimeError("TrainPlattCalibrator must be fitted before predict_proba.")
        s = np.asarray(scores, dtype=np.float64)
        logits = np.clip(self.w * s + self.b, -25.0, 25.0)
        p = 1.0 / (1.0 + np.exp(-logits))
        return np.clip(p, eps, 1.0 - eps).tolist()

    def to_dict(self) -> dict[str, Any]:
        """Export calibrator parameters to dictionary."""
        return {
            "w": self.w,
            "b": self.b,
            "l2_reg": self.l2_reg,
            "max_iter": self.max_iter,
            "lr": self.lr,
            "min_w": self.min_w,
            "fitted": self._fitted,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrainPlattCalibrator:
        """Instantiate calibrator from exported dictionary."""
        cal = cls(
            l2_reg=data.get("l2_reg", 0.1),
            max_iter=data.get("max_iter", 200),
            lr=data.get("lr", 0.05),
            min_w=data.get("min_w", 0.01),
        )
        cal.w = data["w"]
        cal.b = data["b"]
        cal._fitted = data.get("fitted", True)
        return cal


class IsotonicCalibrator:
    """Non-parametric Pool Adjacent Violators Algorithm (PAVA) monotonic step calibrator.

    Fitted strictly on training pairs (score, label); yields non-decreasing step responses.
    """

    def __init__(self) -> None:
        self.thresholds: list[float] = []
        self.probabilities: list[float] = []
        self._fitted = False

    def fit(self, scores: Sequence[float], labels: Sequence[int | float]) -> IsotonicCalibrator:
        s = np.asarray(scores, dtype=np.float64)
        y = np.asarray(labels, dtype=np.float64)
        if len(s) != len(y) or len(s) == 0:
            raise ValueError("Scores and labels must be aligned non-empty sequences.")

        # Sort by score ascending
        order = np.argsort(s)
        s_sorted = s[order]
        y_sorted = y[order]

        # Pool Adjacent Violators Algorithm (PAVA)
        weights = [1.0] * len(y_sorted)
        values = list(y_sorted)
        block_s = list(s_sorted)

        i = 0
        while i < len(values) - 1:
            if values[i] > values[i + 1]:
                # Pool adjacent blocks
                new_w = weights[i] + weights[i + 1]
                new_v = (weights[i] * values[i] + weights[i + 1] * values[i + 1]) / new_w
                values[i] = new_v
                weights[i] = new_w
                del values[i + 1]
                del weights[i + 1]
                del block_s[i + 1]
                # Check backwards
                if i > 0:
                    i -= 1
            else:
                i += 1

        self.thresholds = block_s
        self.probabilities = values
        self._fitted = True
        return self

    def predict_proba(self, scores: Sequence[float], eps: float = 1e-6) -> list[float]:
        if not self._fitted:
            raise RuntimeError("IsotonicCalibrator must be fitted before predict_proba.")
        s = np.asarray(scores, dtype=np.float64)
        # Piecewise step evaluation
        idx = np.searchsorted(self.thresholds, s, side="right") - 1
        idx = np.clip(idx, 0, len(self.probabilities) - 1)
        probs = [self.probabilities[i] for i in idx]
        return np.clip(probs, eps, 1.0 - eps).tolist()

    def to_dict(self) -> dict[str, Any]:
        """Export isotonic thresholds and probabilities."""
        return {
            "thresholds": list(self.thresholds),
            "probabilities": list(self.probabilities),
            "fitted": self._fitted,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IsotonicCalibrator:
        """Instantiate isotonic calibrator from exported dictionary."""
        cal = cls()
        cal.thresholds = list(data["thresholds"])
        cal.probabilities = list(data["probabilities"])
        cal._fitted = data.get("fitted", True)
        return cal


def out_of_fold_calibration(
    scores: Sequence[float],
    labels: Sequence[int | float],
    calibrator_cls: type = TrainPlattCalibrator,
    n_splits: int = 2,
    seed: int = 42,
) -> tuple[list[float], Any]:
    """Perform out-of-fold calibration strictly on development/training data.

    Splits the training set into K folds, fitting the calibrator on K-1 folds
    and predicting on the held-out fold to generate unbiased development probabilities.
    Also returns a master calibrator fitted on all development observations for
    application to subsequent holdouts.
    """
    s = np.asarray(scores, dtype=np.float64)
    y = np.asarray(labels, dtype=np.float64)
    n = len(s)
    if n < n_splits * 2:
        # If dataset is small, use leave-one-out
        n_splits = max(2, n // 2)

    rng = np.random.default_rng(seed)
    indices = np.arange(n)
    rng.shuffle(indices)

    oof_probs = np.zeros(n, dtype=np.float64)
    folds = np.array_split(indices, n_splits)

    for fold_idx, val_idx in enumerate(folds):
        train_idx = np.setdiff1d(indices, val_idx)
        cal = calibrator_cls()
        cal.fit(s[train_idx], y[train_idx])
        oof_probs[val_idx] = cal.predict_proba(s[val_idx])

    # Fit final master calibrator on complete development cohort
    master_cal = calibrator_cls()
    master_cal.fit(s, y)

    return oof_probs.tolist(), master_cal
