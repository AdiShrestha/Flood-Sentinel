"""Portable CPU replay for saved Flood Sentinel classifier checkpoints.

The caller supplies a local manifest naming the processed bundle, selected
weights, validation thresholds, and prediction ledgers. This module never
fetches observations or infers source availability.
"""
from __future__ import annotations

import gzip
import json
import math
from pathlib import Path
import platform
import resource
import sys
import time
from typing import Any

import numpy as np
import torch
from torch import nn

from .ea_lstm import EALSTMCell
from .model import CausalHydroEncoder


HORIZONS = (24, 48, 72)
SEED_ARMS = {"no_ssl_tcn", "ea_lstm", "score_d_transfer"}
PRIMARY_SUPPORT = "primary_common_known_scoreable_complete_forcing"


class _BinaryTCN(nn.Module):
    def __init__(self, encoder: CausalHydroEncoder) -> None:
        super().__init__()
        self.encoder = encoder
        self.horizon_head = nn.Linear(encoder.d_model, 3)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.horizon_head(self.encoder(x)[:, -1, :])


class _EAThree(nn.Module):
    def __init__(self, dynamic_dim: int = 6, static_dim: int = 10, hidden_dim: int = 32) -> None:
        super().__init__()
        self.cell = EALSTMCell(dynamic_dim, static_dim, hidden_dim)
        self.head = nn.Linear(hidden_dim, 3)

    def forward(self, dynamic: torch.Tensor, static: torch.Tensor) -> torch.Tensor:
        gate = torch.sigmoid(self.cell.w_i(static))
        batch, steps, _ = dynamic.shape
        hidden = dynamic.new_zeros((batch, self.cell.hidden_dim))
        cell = dynamic.new_zeros((batch, self.cell.hidden_dim))
        for step in range(steps):
            hidden, cell = self.cell(dynamic[:, step, :], hidden, cell, gate)
        return self.head(hidden)


def _resolve(base: Path, value: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("manifest paths must be nonempty strings")
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def _json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _jsonl_gz(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_jsonl_gz(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, compresslevel=6) as compressed:
            for row in records:
                data = json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False)
                compressed.write((data + "\n").encode("utf-8"))


def _metric(y_values: list[int], scores: list[float], threshold: float) -> dict[str, Any]:
    y = np.asarray(y_values, dtype=np.int8)
    score = np.asarray(scores, dtype=np.float64)
    n = int(len(y))
    positive = int(y.sum())
    negative = n - positive
    result: dict[str, Any] = {"n": n, "positive": positive, "negative": negative}
    if not n:
        return {**result, "average_precision": None, "pr_auc_trapezoid": None,
                "auroc": None, "brier": None, "log_loss_exact": None,
                "log_loss_exact_status": "undefined_empty_support",
                "log_loss_exact_infinite_count": 0, "log_loss_clipped_1e-7": None}

    if positive:
        order = np.argsort(-score, kind="mergesort")
        sorted_score = score[order]
        sorted_y = y[order]
        cumulative_tp = np.cumsum(sorted_y)
        group_ends = np.r_[np.flatnonzero(np.diff(sorted_score)), n - 1]
        tp = cumulative_tp[group_ends].astype(np.float64)
        fp = (group_ends + 1).astype(np.float64) - tp
        recall = tp / positive
        precision = tp / (tp + fp)
        previous_recall = np.r_[0.0, recall[:-1]]
        result["average_precision"] = float(np.sum((recall - previous_recall) * precision))
        # sklearn's trapezoidal precision-recall AUC includes (recall=0, precision=1).
        pr_recall = np.r_[0.0, recall]
        pr_precision = np.r_[1.0, precision]
        result["pr_auc_trapezoid"] = float(np.sum((pr_precision[:-1] + pr_precision[1:]) * np.diff(pr_recall) / 2))
    else:
        result["average_precision"] = None
        result["pr_auc_trapezoid"] = None

    if positive and negative:
        order = np.argsort(score, kind="mergesort")
        ranks = np.empty(n, dtype=np.float64)
        sorted_score = score[order]
        first = 0
        while first < n:
            end = first + 1
            while end < n and sorted_score[end] == sorted_score[first]:
                end += 1
            average_rank = (first + 1 + end) / 2.0
            ranks[order[first:end]] = average_rank
            first = end
        rank_sum = float(ranks[y == 1].sum())
        result["auroc"] = (rank_sum - positive * (positive + 1) / 2.0) / (positive * negative)
    else:
        result["auroc"] = None

    alerts = score >= float(threshold)
    tp = int(np.sum(alerts & (y == 1)))
    fp = int(np.sum(alerts & (y == 0)))
    tn = int(np.sum(~alerts & (y == 0)))
    fn = int(np.sum(~alerts & (y == 1)))
    result.update({
        "threshold": float(threshold), "alerts": int(alerts.sum()), "tp": tp,
        "fp": fp, "tn": tn, "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / positive if positive else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
    })
    if np.any((score < 0) | (score > 1)):
        raise ValueError("replayed classifier probability is outside [0, 1]")
    exact_terms: list[float] = []
    infinite_count = 0
    for observed, probability in zip(y, score):
        if observed and probability == 0.0:
            infinite_count += 1
        elif not observed and probability == 1.0:
            infinite_count += 1
        elif observed:
            exact_terms.append(-math.log(float(probability)))
        else:
            exact_terms.append(-math.log1p(-float(probability)))
    clipped = np.clip(score, 1e-7, 1.0 - 1e-7)
    result.update({
        "brier": float(np.mean((score - y) ** 2)),
        "log_loss_exact": None if infinite_count else float(np.mean(exact_terms)),
        "log_loss_exact_status": "infinite" if infinite_count else "finite",
        "log_loss_exact_infinite_count": infinite_count,
        "log_loss_clipped_1e-7": float(-np.mean(y * np.log(clipped) + (1 - y) * np.log1p(-clipped))),
    })
    return result


def _model(kind: str, architecture: dict[str, Any]) -> nn.Module:
    if kind == "ea_lstm":
        return _EAThree(
            dynamic_dim=int(architecture.get("dynamic_dim", 6)),
            static_dim=int(architecture.get("static_dim", 10)),
            hidden_dim=int(architecture.get("hidden_dim", 32)),
        )
    if kind not in {"no_ssl_tcn", "score_d_transfer"}:
        raise ValueError(f"unsupported model_kind: {kind}")
    encoder_config = architecture.get("encoder", architecture)
    encoder = CausalHydroEncoder(
        in_channels=int(encoder_config.get("in_channels", 6)),
        d_model=int(encoder_config.get("d_model", 32)),
        tcn_layers=int(encoder_config.get("tcn_layers", 9)),
        transformer_layers=int(encoder_config.get("transformer_layers", 0)),
        n_heads=int(encoder_config.get("n_heads", 4)),
        d_ff=int(encoder_config.get("d_ff", 128)),
        dropout=float(encoder_config.get("dropout", 0.1)),
    )
    return _BinaryTCN(encoder)


def _max_abs(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return math.inf
    return max((abs(float(a) - float(b)) for a, b in zip(left, right)), default=0.0)


_EXACT_METRIC_COUNTS = (
    "n", "positive", "negative", "tp", "fp", "tn", "fn", "alerts",
    "log_loss_exact_infinite_count",
)
_EXACT_METRIC_STATUSES = ("log_loss_exact_status",)
_TOLERANCED_METRIC_VALUES = (
    "threshold", "average_precision", "auroc", "pr_auc_trapezoid",
    "precision", "recall", "f1", "brier", "log_loss_exact",
    "log_loss_clipped_1e-7",
)


def _compare_metric_records(
    actual: dict[str, Any], expected: dict[str, Any], atol: float
) -> tuple[dict[str, float], list[str]]:
    """Compare replay metrics, preserving exact support and exact-loss state."""
    diffs: dict[str, float] = {}
    mismatches: list[str] = []
    missing = object()

    for key in _EXACT_METRIC_COUNTS:
        left, right = actual.get(key, missing), expected.get(key, missing)
        if type(left) is not int or type(right) is not int or left != right:
            mismatches.append(f"{key}: {left!r} != {right!r}")

    for key in _EXACT_METRIC_STATUSES:
        left, right = actual.get(key, missing), expected.get(key, missing)
        if not isinstance(left, str) or not isinstance(right, str) or left != right:
            mismatches.append(f"{key}: {left!r} != {right!r}")

    for key in _TOLERANCED_METRIC_VALUES:
        left, right = actual.get(key, missing), expected.get(key, missing)
        if left is missing or right is missing:
            mismatches.append(f"{key}: missing from actual or expected metric record")
        elif left is None or right is None:
            if left is not right:
                mismatches.append(f"{key}: {left!r} != {right!r}")
        else:
            try:
                left_value, right_value = float(left), float(right)
            except (TypeError, ValueError):
                mismatches.append(f"{key}: non-numeric value {left!r} or {right!r}")
                continue
            if not math.isfinite(left_value) or not math.isfinite(right_value):
                mismatches.append(f"{key}: non-finite numeric value {left!r} or {right!r}")
                continue
            diff = abs(left_value - right_value)
            diffs[key] = diff
            if diff > atol:
                mismatches.append(f"{key}: difference {diff:.3g}")

    return diffs, mismatches


def run_replay(manifest_path: str | Path) -> dict[str, Any]:
    """Recompute all requested model outputs, then compare ledgers and primary metrics."""
    overall_wall_start = time.perf_counter()
    overall_cpu_start = time.process_time()
    path = Path(manifest_path).expanduser().resolve()
    base = path.parent
    manifest = _json(path)
    if manifest.get("schema") != "flood-sentinel-local-replay-manifest-v1":
        raise ValueError("unsupported replay manifest schema")
    runs = manifest.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("manifest runs must be a nonempty list")
    identities = [(r.get("model_kind"), int(r.get("seed", -1))) for r in runs]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate model_kind/seed run in manifest")

    bundle = manifest.get("bundle", {})
    source_features = torch.load(_resolve(base, bundle["standardized_backing"]), map_location="cpu", weights_only=True)
    index = torch.load(_resolve(base, bundle["window_index"]), map_location="cpu", weights_only=True)
    target = torch.load(_resolve(base, bundle["targets"]), map_location="cpu", weights_only=True)
    static_blob = torch.load(_resolve(base, bundle["static_attributes"]), map_location="cpu", weights_only=True)
    issue_meta = _jsonl_gz(_resolve(base, bundle["issue_times"]))
    baseline_path = _resolve(base, manifest["baseline_predictions"])
    metric_path = _resolve(base, manifest["expected_paired_metrics"])
    expected_metrics = _json(metric_path)
    baseline_rows = _jsonl_gz(baseline_path)
    baseline = {(r["sample_id"], int(r["horizon_hours"])): r for r in baseline_rows if r["split"] == "TEST"}

    features = source_features["features"].to(dtype=torch.float32, device="cpu")
    windows = index["window_date_indices"].long()
    site_index = index["site_index"].long()
    labels = target["labels"].to(dtype=torch.float32, device="cpu")
    known = target["known_label_mask"].bool()
    static = static_blob["static_features"].to(dtype=torch.float32, device="cpu")
    if len(issue_meta) != len(windows) or labels.shape != known.shape or labels.shape[0] != len(issue_meta):
        raise ValueError("bundle arrays do not align with issue metadata")
    if windows.ndim != 2 or not torch.isfinite(features).all() or not torch.isfinite(static).all():
        raise ValueError("bundle requires finite features/static values and a two-dimensional window index")

    output_dir = _resolve(base, manifest.get("output_dir", "replay-output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(int(manifest.get("torch_threads", 4)))
    batch_size = int(manifest.get("batch_size", 32))
    atol = float(manifest.get("prediction_atol", 1e-6))
    rtol = float(manifest.get("prediction_rtol", 1e-6))
    cutoff = manifest.get("primary_support_cutoff_utc", "2024-11-02T12:00:00Z")
    report_runs: list[dict[str, Any]] = []

    for run in runs:
        run_wall_start = time.perf_counter()
        run_cpu_start = time.process_time()
        kind = run["model_kind"]
        seed = int(run["seed"])
        architecture = run.get("architecture", {})
        model = _model(kind, architecture)
        checkpoint = torch.load(_resolve(base, run["checkpoint"]), map_location="cpu", weights_only=True)
        state = checkpoint.get("model_state_dict")
        if not isinstance(state, dict):
            raise ValueError(f"checkpoint has no model_state_dict: {kind}/{seed}")
        model.load_state_dict(state, strict=True)
        model.eval()
        logits = np.empty((len(issue_meta), len(HORIZONS)), dtype=np.float32)
        with torch.inference_mode():
            for start in range(0, len(issue_meta), batch_size):
                end = min(start + batch_size, len(issue_meta))
                ids = torch.arange(start, end, dtype=torch.long)
                dynamic = features[site_index[ids, None], windows[ids]].to(dtype=torch.float32)
                if kind == "ea_lstm":
                    output = model(dynamic, static[site_index[ids]])
                else:
                    output = model(dynamic)
                logits[start:end] = output.cpu().numpy()
        # Preserve the model's float32 sigmoid path used by the saved prediction
        # ledger; a float64 NumPy sigmoid can shift endpoint-sensitive log loss.
        probabilities = torch.sigmoid(torch.from_numpy(logits)).numpy().astype(np.float64)
        thresholds_doc = _json(_resolve(base, run["validation_thresholds"]))
        threshold_values = {h: thresholds_doc["thresholds"][str(h)]["threshold"] for h in HORIZONS}
        saved = _jsonl_gz(_resolve(base, run["saved_predictions"]))
        saved_map = {(r["sample_id"], int(r["horizon_hours"])): r for r in saved}
        if len(saved_map) != len(issue_meta) * len(HORIZONS):
            raise ValueError(f"saved prediction ledger has unexpected row count: {kind}/{seed}")

        replay_rows: list[dict[str, Any]] = []
        logit_diffs: list[float] = []
        probability_diffs: list[float] = []
        logit_pairs: list[tuple[float, float]] = []
        probability_pairs: list[tuple[float, float]] = []
        label_mismatches = 0
        for i, meta in enumerate(issue_meta):
            for j, horizon in enumerate(HORIZONS):
                old = saved_map[(meta["sample_id"], horizon)]
                p = float(probabilities[i, j])
                z = float(logits[i, j])
                old_p = float(old["probability"])
                old_z = float(old["logit"])
                logit_diffs.append(abs(z - old_z))
                probability_diffs.append(abs(p - old_p))
                logit_pairs.append((z, old_z))
                probability_pairs.append((p, old_p))
                truth = int(labels[i, j]) if bool(known[i, j]) else None
                if old.get("target_mask") != bool(known[i, j]) or old.get("label") != truth:
                    label_mismatches += 1
                threshold = threshold_values[horizon]
                replay_rows.append({
                    "sample_id": meta["sample_id"], "site_id": meta["site_id"],
                    "issue_time_utc": meta["issue_time_utc"], "split": meta["split"],
                    "horizon_hours": horizon,
                    "label_status": target["label_state"][i][j], "label": truth,
                    "target_mask": bool(known[i, j]), "logit": z, "probability": p,
                    "threshold": threshold, "alert": bool(p >= threshold) if threshold is not None else None,
                    "complete_forcing_support": meta["issue_time_utc"] <= cutoff if meta["split"] == "TEST" else None,
                })

        y_by_horizon: dict[int, list[int]] = {}
        p_by_horizon: dict[int, list[float]] = {}
        threshold_by_horizon = threshold_values
        support_counts: dict[str, dict[str, int]] = {}
        for horizon in HORIZONS:
            ys: list[int] = []
            ps: list[float] = []
            eligible = 0
            unknown = 0
            for i, meta in enumerate(issue_meta):
                if meta["split"] != "TEST" or meta["issue_time_utc"] > cutoff:
                    continue
                eligible += 1
                row = baseline.get((meta["sample_id"], horizon))
                if row is None:
                    raise ValueError("baseline ledger is missing a TEST issue/horizon")
                if not bool(known[i, horizon // 24 - 1]):
                    unknown += 1
                    continue
                if not all(value is not None and math.isfinite(float(value)) for value in row["scores"].values()):
                    continue
                ys.append(int(labels[i, horizon // 24 - 1]))
                ps.append(float(probabilities[i, horizon // 24 - 1]))
            y_by_horizon[horizon] = ys
            p_by_horizon[horizon] = ps
            support_counts[str(horizon)] = {"eligible_issue_denominator": eligible,
                                             "unknown_or_purged_labels": unknown,
                                             "known_scoreable_denominator": len(ys),
                                             "positive": int(sum(ys))}

        metric_diffs: dict[str, dict[str, float]] = {}
        mismatches: list[str] = []
        for horizon in HORIZONS:
            hkey = str(horizon)
            actual = _metric(y_by_horizon[horizon], p_by_horizon[horizon], threshold_by_horizon[horizon])
            expected = expected_metrics["paired_results"][hkey][str(seed)][kind][PRIMARY_SUPPORT]["pooled"]
            metric_diffs[hkey], cell_mismatches = _compare_metric_records(
                actual, expected, float(manifest.get("metric_atol", 1e-10))
            )
            mismatches.extend(f"{hkey}/{item}" for item in cell_mismatches)

        output_path = output_dir / f"{kind}_seed{seed}_replayed.jsonl.gz"
        _write_jsonl_gz(output_path, replay_rows)
        report_runs.append({
            "model_kind": kind, "seed": seed,
            "checkpoint_epoch": checkpoint.get("epoch"),
            "prediction_rows": len(replay_rows),
            "max_abs_logit_difference": max(logit_diffs, default=0.0),
            "max_abs_probability_difference": max(probability_diffs, default=0.0),
            "prediction_values_within_tolerance": all(
                np.isclose(a, b, atol=atol, rtol=rtol) for a, b in logit_pairs
            ) and all(np.isclose(a, b, atol=atol, rtol=rtol) for a, b in probability_pairs),
            "label_or_mask_mismatches": label_mismatches,
            "primary_support_by_horizon": support_counts,
            "max_abs_metric_differences": metric_diffs,
            "metric_mismatches": mismatches,
            "replayed_predictions": output_path.name,
            "replay_wall_seconds": time.perf_counter() - run_wall_start,
            "replay_process_cpu_seconds": time.process_time() - run_cpu_start,
        })

    report = {
        "schema": "flood-sentinel-portable-replay-report-v1",
        "replay_manifest_schema": manifest["schema"],
        "python_version": sys.version.split()[0], "platform": platform.platform(),
        "torch_version": torch.__version__, "numpy_version": np.__version__,
        "device": "cpu", "torch_threads": torch.get_num_threads(),
        "process_wall_seconds": time.perf_counter() - overall_wall_start,
        "process_cpu_seconds": time.process_time() - overall_cpu_start,
        "process_peak_rss_native": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "process_peak_rss_unit": "bytes on macOS; platform-specific elsewhere",
        "expected_prediction_tolerance": {"atol": atol, "rtol": rtol},
        "expected_metric_absolute_tolerance": float(manifest.get("metric_atol", 1e-10)),
        "runs": report_runs,
        "all_prediction_and_metric_checks_pass": all(
            r["prediction_values_within_tolerance"] and r["label_or_mask_mismatches"] == 0 and not r["metric_mismatches"]
            for r in report_runs
        ),
    }
    report_path = output_dir / "replay_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    if not report["all_prediction_and_metric_checks_pass"]:
        raise RuntimeError(f"replay comparison failed; inspect {report_path}")
    return report
