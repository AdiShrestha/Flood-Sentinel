"""Clean pipeline replay verification and bitwise reproducibility auditing.

Verifies that model checkpoints, persistent normalizers, and deterministic baseline
comparators reproduce canonical evaluation predictions within strict numerical
tolerances (|Δ| < 1e-6).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping, Sequence

import numpy as np
import torch

from flood_sentinel.dataset import CausalHydroDataset, create_dataloader
try:
    from runners.run_experiment import parse_model_family, run_experiment
except ImportError:
    from source.runners.run_experiment import parse_model_family, run_experiment


def compare_prediction_series(
    recorded_records: Sequence[Mapping[str, Any]],
    replayed_records: Sequence[Mapping[str, Any]],
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    """Compare recorded and replayed prediction records by ``sample_id``.

    The comparison is complete, not an intersection: missing, extra or
    duplicated sample IDs and non-finite scores make the replay fail
    (``within_tolerance`` and ``bitwise_identical`` are False) and are
    reported. Score differences are computed over the shared IDs only for
    diagnosis.
    """
    def _index(records: Sequence[Mapping[str, Any]]) -> tuple[dict[str, float], list[str]]:
        mapping: dict[str, float] = {}
        duplicates: list[str] = []
        for r in records:
            sid = str(r["sample_id"])
            if sid in mapping:
                duplicates.append(sid)
            mapping[sid] = float(r["score"])
        return mapping, sorted(set(duplicates))

    rec_map, rec_dups = _index(recorded_records)
    rep_map, rep_dups = _index(replayed_records)

    common_ids = sorted(set(rec_map.keys()) & set(rep_map.keys()))
    if not common_ids:
        raise ValueError("No common sample_ids found between recorded and replayed predictions.")
    missing_ids = sorted(set(rec_map) - set(rep_map))
    extra_ids = sorted(set(rep_map) - set(rec_map))
    nonfinite_ids = sorted(
        sid for sid in common_ids
        if not (np.isfinite(rec_map[sid]) and np.isfinite(rep_map[sid]))
    )

    diffs = [abs(rec_map[sid] - rep_map[sid]) for sid in common_ids if sid not in nonfinite_ids]
    max_diff = float(np.max(diffs)) if diffs else float("nan")
    mean_diff = float(np.mean(diffs)) if diffs else float("nan")
    complete = not (missing_ids or extra_ids or rec_dups or rep_dups or nonfinite_ids)
    within_tol = bool(complete and max_diff <= tolerance)
    bitwise_identical = bool(complete and max_diff == 0.0)

    return {
        "n_samples": len(common_ids),
        "n_recorded": len(rec_map),
        "n_replayed": len(rep_map),
        "missing_sample_ids": missing_ids,
        "extra_sample_ids": extra_ids,
        "duplicate_recorded_ids": rec_dups,
        "duplicate_replayed_ids": rep_dups,
        "nonfinite_sample_ids": nonfinite_ids,
        "complete_id_match": complete,
        "max_absolute_error": max_diff,
        "mean_absolute_error": mean_diff,
        "within_tolerance": within_tol,
        "bitwise_identical": bitwise_identical,
        "tolerance": tolerance,
    }


def audit_run_replay(
    run_attempt_dir: Path,
    cohort_path: Path,
    src_path: Path,
    seed: int,
    experiment_id: str,
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    """Execute clean replay of an experiment run in an isolated directory and audit predictions."""
    pred_path = run_attempt_dir / "predictions.csv"
    if not pred_path.is_file():
        raise FileNotFoundError(f"Missing predictions.csv in {run_attempt_dir}")

    with pred_path.open(encoding="utf-8") as f:
        recorded_preds = list(csv.DictReader(f))

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_run_dir = Path(tmp_dir)
        run_experiment(tmp_run_dir, seed=seed, experiment_id=experiment_id)

        tmp_pred_path = tmp_run_dir / "predictions.csv"
        with tmp_pred_path.open(encoding="utf-8") as f:
            replayed_preds = list(csv.DictReader(f))

    diff_meta = compare_prediction_series(recorded_preds, replayed_preds, tolerance=tolerance)

    # Checkpoint and artifact inspection
    has_checkpoint = (run_attempt_dir / "checkpoint.pt").is_file()
    has_history = (run_attempt_dir / "history.csv").is_file()
    has_method = (run_attempt_dir / "method.txt").is_file()

    return {
        "experiment_id": experiment_id,
        "seed": seed,
        "family": parse_model_family(experiment_id),
        "run_dir": str(run_attempt_dir),
        "has_checkpoint": has_checkpoint,
        "has_history": has_history,
        "has_method": has_method,
        # Not checked by this audit; reported as unverified rather than assumed.
        "normalizer_compatible": None,
        "dataset_split_compatible": None,
        **diff_meta,
    }
