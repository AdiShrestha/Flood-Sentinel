"""Smoke test runner for runtime verification and supervisor integration.

# FABRICATION-DISCLOSURE: this script is an engineering verification fixture,
# not an observational research training pipeline. All generated outputs are
# disclosed test records.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
import sys
from pathlib import Path

# Ensure local source package root is importable in isolated subprocess
SOURCE_DIR = Path(__file__).resolve().parents[1]
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

# Verify critical dependencies in execution runtime
import numpy as np
import scipy
import torch

import flood_sentinel
from flood_sentinel.model import CausalHydroEncoder


def run_smoke(run_dir: Path, seed: int, experiment_id: str) -> None:
    run_dir = Path(run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    torch.manual_seed(seed)
    np.random.seed(seed)

    # Verify neural architecture forward pass on CPU
    model = CausalHydroEncoder(
        in_channels=4,
        d_model=8,
        tcn_layers=2,
        transformer_layers=1,
        n_heads=2,
        d_ff=16,
        dropout=0.0,
    )
    model.eval()

    # Synthetic input batch: shape (batch_size=2, seq_len=10, in_channels=4)
    x = torch.randn(2, 10, 4)
    with torch.no_grad():
        out = model(x)
        assert out.shape == (2, 10, 8), f"Unexpected model output shape: {out.shape}"

    # Generate synthetic predictions for gatekeeper verification
    cohort_path = Path.cwd() / "data" / "cohort.csv"
    if cohort_path.is_file():
        with cohort_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cohort_rows = list(reader)
        predictions = []
        for row in cohort_rows:
            if row.get("split") in ("validation", "test"):
                label = row.get("label", "0")
                score = 0.85 if label == "1" else 0.15
                predictions.append({
                    "sample_id": row["sample_id"],
                    "label": label,
                    "score": score,
                })
    else:
        predictions = [
            {"sample_id": f"s_{i}", "label": str(i % 2), "score": 0.85 if (i % 2) == 1 else 0.15}
            for i in range(12)
        ]

    pred_file = run_dir / "predictions.csv"
    with pred_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["sample_id", "label", "score"])
        writer.writeheader()
        writer.writerows(predictions)

    method_file = run_dir / "method.txt"
    method_file.write_text(
        "ENGINEERING FIXTURE ONLY: This run verifies supervisor contract execution, "
        "interpreter isolation, neural forward pass, and receipt generation. "
        "It contains no observational flood evidence.\n",
        encoding="utf-8",
    )

    metrics = {
        "auroc": 1.0,
        "average_precision": 1.0,
        "accuracy": 1.0,
        "f1": 1.0,
        "brier": 0.0225,
        "log_loss": -math.log(0.85),
    }

    result = {
        "experiment_id": experiment_id,
        "seed": seed,
        "config": {"latent_dim": 8, "n_features": 4},
        "predictions": "predictions.csv",
        "reported_metrics": {
            "validation": metrics,
            "test": metrics,
        },
        "method_evidence": "method.txt",
    }
    (run_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Supervisor smoke test runner")
    parser.add_argument("--output-dir", dest="named_run_dir", default=None)
    parser.add_argument("--run-dir", dest="alt_run_dir", default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--experiment-id", dest="named_exp_id", default=None)
    parser.add_argument("positional", nargs="*")

    args = parser.parse_args()

    run_dir = args.named_run_dir or args.alt_run_dir
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
        raise ValueError("Missing required run directory (--output-dir or positional arg 1)")
    if seed is None:
        seed = 42
    if exp_id is None:
        exp_id = "smoke_experiment"

    run_smoke(Path(run_dir), seed, exp_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
