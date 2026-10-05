"""Independent metric recomputation tool.

CRITICAL INVARIANT:
This module contains ZERO imports from factory.engine.metrics or any factory package.
All arithmetic is derived from first mathematical principles.
"""
from __future__ import annotations

import itertools
import math
import random
from typing import Mapping, Sequence


class RecomputationDiscrepancyError(ValueError):
    """Raised when independently recomputed metrics diverge from reference values beyond tolerance."""
    pass


def _to_float_vector(values: Sequence[float | int], name: str) -> list[float]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{name} must be a sequence of numbers, not string/bytes.")
    out: list[float] = []
    for i, v in enumerate(values):
        if isinstance(v, bool):
            raise ValueError(f"Boolean value at index {i} in {name} is not allowed.")
        try:
            fv = float(v)
        except (TypeError, ValueError) as err:
            raise ValueError(f"Non-numeric value {v!r} at index {i} in {name}") from err
        if not math.isfinite(fv):
            raise ValueError(f"Non-finite value {fv} at index {i} in {name}")
        out.append(fv)
    return out


def recompute_auroc(labels: Sequence[int], scores: Sequence[float]) -> float:
    """Independent Mann-Whitney rank sum AUROC with mid-rank tie handling."""
    y = _to_float_vector(labels, "labels")
    s = _to_float_vector(scores, "scores")
    n = len(y)
    if n != len(s) or n == 0 or set(y) != {0.0, 1.0}:
        raise ValueError("AUROC requires non-empty binary labels with both classes present.")

    pos = sum(y)
    neg = n - pos
    # Sort pairs by score ascending
    pairs = sorted(zip(s, y), key=lambda x: x[0])

    rank_sum = 0.0
    i = 0
    while i < n:
        j = i + 1
        while j < n and pairs[j][0] == pairs[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        pos_in_group = sum(p[1] for p in pairs[i:j])
        rank_sum += avg_rank * pos_in_group
        i = j

    auroc = (rank_sum - pos * (pos + 1.0) / 2.0) / (pos * neg)
    return float(auroc)


def recompute_average_precision(labels: Sequence[int], scores: Sequence[float]) -> float:
    """Independent non-interpolated Average Precision with grouped tied thresholds."""
    y = _to_float_vector(labels, "labels")
    s = _to_float_vector(scores, "scores")
    n = len(y)
    if n != len(s) or n == 0 or set(y) != {0.0, 1.0}:
        raise ValueError("AP requires non-empty binary labels with both classes present.")

    pos = sum(y)
    # Sort pairs by score descending
    pairs = sorted(zip(s, y), key=lambda x: x[0], reverse=True)

    tp = 0.0
    seen = 0
    ap = 0.0
    i = 0
    while i < n:
        j = i + 1
        while j < n and pairs[j][0] == pairs[i][0]:
            j += 1
        added_tp = sum(p[1] for p in pairs[i:j])
        tp += added_tp
        seen += (j - i)
        ap += (added_tp / pos) * (tp / seen)
        i = j

    return float(ap)


def recompute_classification_metrics(
    labels: Sequence[int],
    scores: Sequence[float],
    threshold: float = 0.5,
) -> dict[str, float]:
    """Independent accuracy, precision, recall, and F1."""
    y = _to_float_vector(labels, "labels")
    s = _to_float_vector(scores, "scores")
    n = len(y)
    if n != len(s) or n == 0:
        raise ValueError("Labels and scores must be aligned non-empty sequences.")

    thresh = float(threshold)
    preds = [int(v >= thresh) for v in s]

    tp = sum(a == 1.0 and b == 1 for a, b in zip(y, preds))
    fp = sum(a == 0.0 and b == 1 for a, b in zip(y, preds))
    fn = sum(a == 1.0 and b == 0 for a, b in zip(y, preds))
    tn = sum(a == 0.0 and b == 0 for a, b in zip(y, preds))

    acc = (tp + tn) / n
    f1 = 2.0 * tp / (2.0 * tp + fp + fn) if (2.0 * tp + fp + fn) > 0 else 0.0
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    return {
        "accuracy": float(acc),
        "f1": float(f1),
        "precision": float(prec),
        "recall": float(rec),
        "tp": float(tp),
        "fp": float(fp),
        "fn": float(fn),
        "tn": float(tn),
    }


def recompute_probabilistic_metrics(
    labels: Sequence[int],
    probabilities: Sequence[float],
    log_epsilon: float = 1e-15,
) -> dict[str, float]:
    """Independent Brier score, log-loss, and Brier Skill Score."""
    y = _to_float_vector(labels, "labels")
    p = _to_float_vector(probabilities, "probabilities")
    n = len(y)
    if n != len(p) or n == 0:
        raise ValueError("Labels and probabilities must be aligned non-empty sequences.")

    for val in p:
        if not (0.0 <= val <= 1.0):
            raise ValueError(f"Probabilities must be in [0, 1], got {val}")

    eps = float(log_epsilon)
    brier = sum((prob - label) ** 2 for prob, label in zip(p, y)) / n

    log_loss_sum = 0.0
    for label, prob in zip(y, p):
        clipped_p = min(1.0 - eps, max(eps, prob))
        log_loss_sum += label * math.log(clipped_p) + (1.0 - label) * math.log(1.0 - clipped_p)
    log_loss = -log_loss_sum / n

    # Climatology Brier reference (sample prevalence)
    base_rate = sum(y) / n
    ref_brier = base_rate * (1.0 - base_rate)
    bss = 1.0 - (brier / ref_brier) if ref_brier > 0 else 0.0

    return {
        "brier": float(brier),
        "log_loss": float(log_loss),
        "brier_skill_score": float(bss),
    }


def recompute_binary_metrics(
    labels: Sequence[int],
    scores: Sequence[float],
    threshold: float = 0.5,
    log_epsilon: float = 1e-15,
) -> dict[str, float]:
    """Recompute full binary suite matching standard evaluation fields."""
    auroc = recompute_auroc(labels, scores)
    ap = recompute_average_precision(labels, scores)
    clf = recompute_classification_metrics(labels, scores, threshold)
    prob = recompute_probabilistic_metrics(labels, scores, log_epsilon)

    return {
        "auroc": auroc,
        "average_precision": ap,
        "accuracy": clf["accuracy"],
        "f1": clf["f1"],
        "brier": prob["brier"],
        "log_loss": prob["log_loss"],
    }


def _regularized_beta_fraction(a: float, b: float, x: float) -> float:
    """Continued fraction for regularized incomplete beta (Lentz method)."""
    tiny = 1e-300
    c, d = 1.0, 1.0 - (a + b) * x / (a + 1.0)
    d = 1.0 / (d if abs(d) >= tiny else tiny)
    result = d
    for m in range(1, 301):
        m2 = 2 * m
        for term in (
            m * (b - m) * x / ((a + m2 - 1.0) * (a + m2)),
            -(a + m) * (a + b + m) * x / ((a + m2) * (a + m2 + 1.0)),
        ):
            d = 1.0 + term * d
            d = 1.0 / (d if abs(d) >= tiny else tiny)
            c = 1.0 + term / c
            if abs(c) < tiny:
                c = tiny
            change = c * d
            result *= change
        if abs(change - 1.0) < 3e-14:
            return result
    raise ValueError("Student-t beta fraction did not converge.")


def _regularized_beta(x: float, a: float, b: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _regularized_beta_fraction(a, b, x) / a
    return 1.0 - front * _regularized_beta_fraction(b, a, 1.0 - x) / b


def recompute_student_t_critical(alpha: float, df: int) -> float:
    """Two-sided Student-t critical value via bisection."""
    if not (0.0 < alpha < 1.0) or df < 1:
        raise ValueError("Invalid alpha or degrees of freedom for Student-t.")
    low, high = 0.0, 1.0

    def tail(val: float) -> float:
        return _regularized_beta(df / (df + val * val), df / 2.0, 0.5)

    while tail(high) > alpha:
        high *= 2.0
        if not math.isfinite(high * high):
            raise ValueError("Student-t critical overflow.")

    for _ in range(80):
        mid = (low + high) / 2.0
        if tail(mid) > alpha:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0


def recompute_paired_sign_flip_pvalue(
    diffs: Sequence[float],
    seed: int = 314159,
    draws: int = 10000,
) -> float:
    """Two-sided paired sign-flip permutation test p-value."""
    d = _to_float_vector(diffs, "paired diffs")
    n = len(d)
    if n < 2:
        raise ValueError("Paired inference requires >= 2 units.")

    observed = sum(d) / n
    tol = max(math.ulp(abs(observed)) * 8, abs(observed) * 1e-12)

    def is_extreme(val: float) -> bool:
        return abs(val) >= abs(observed) - tol

    if n <= 16:
        # Exact enumeration of all 2^n sign assignments
        extreme = 0
        total = 2 ** n
        for signs in itertools.product((-1, 1), repeat=n):
            perm_mean = sum(x * s for x, s in zip(d, signs)) / n
            if is_extreme(perm_mean):
                extreme += 1
        return extreme / total
    else:
        rng = random.Random(seed)
        extreme = 0
        for _ in range(draws):
            signs = [rng.choice((-1, 1)) for _ in range(n)]
            perm_mean = sum(x * s for x, s in zip(d, signs)) / n
            if is_extreme(perm_mean):
                extreme += 1
        return (extreme + 1.0) / (draws + 1.0)


def recompute_holm(pvalues: Sequence[float]) -> list[float]:
    """Holm step-down adjusted p-values."""
    vals = _to_float_vector(pvalues, "pvalues")
    m = len(vals)
    for p in vals:
        if not (0.0 <= p <= 1.0):
            raise ValueError(f"p-value {p} outside [0, 1]")

    sorted_indices = sorted(range(m), key=lambda i: vals[i])
    out = [0.0] * m
    cum_max = 0.0
    for rank, idx in enumerate(sorted_indices):
        raw_p = vals[idx]
        adj_p = min(1.0, (m - rank) * raw_p)
        cum_max = max(cum_max, adj_p)
        out[idx] = float(cum_max)
    return out


def verify_metric_parity(
    independent: Mapping[str, float],
    reference: Mapping[str, float],
    atol: float = 1e-12,
) -> None:
    """Verify that independent recomputed metrics match reference values within absolute tolerance."""
    for key, indep_val in independent.items():
        if key not in reference:
            continue
        ref_val = reference[key]
        diff = abs(indep_val - ref_val)
        if diff > atol:
            raise RecomputationDiscrepancyError(
                f"Metric discrepancy for '{key}': independent={indep_val:.16e}, "
                f"reference={ref_val:.16e}, diff={diff:.6e} > tolerance {atol:.1e}"
            )
