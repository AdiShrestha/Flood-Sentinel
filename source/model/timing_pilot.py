"""Compute-Budget Timing Pilot Gate (C04-03 / §4b / NFR-001).

Executes an empirical CPU timing benchmark on a sample slice of training windows,
measures wall-clock training throughput, extrapolates full-corpus pretraining duration,
and validates against the 2.0-hour compute budget limit.
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.model.c_encoder import CEncoderPretrainModel
from source.utils.config import CHUNK03_DIR, CHUNK04_DIR
from source.utils.logging_config import get_logger

logger = get_logger("timing_pilot")


def run_timing_pilot(
    slice_size: int = 128,
    batch_size: int = 64,
    total_train_windows: int = 9760,
    target_epochs: int = 10,
    max_budget_hours: float = 2.0
) -> Dict[str, Any]:
    """Measure empirical CPU throughput and extrapolate pretraining runtime."""
    logger.info(f"Initiating Compute-Budget Timing Pilot (Slice: {slice_size} windows, Batch: {batch_size})...")

    # Construct synthetic/empirical test tensor: (slice_size, 365, 6)
    T, C = 365, 6
    x_sample = torch.randn(slice_size, T, C, dtype=torch.float32)
    dataset = TensorDataset(x_sample)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

    model = CEncoderPretrainModel(in_channels=C, d_model=64, tcn_layers=3, transformer_layers=2)
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.MSELoss()

    # 1. Warm-up step
    for (batch_x,) in dataloader:
        optimizer.zero_grad()
        _, recon = model(batch_x)
        loss = criterion(recon, batch_x)
        loss.backward()
        optimizer.step()
        break

    # 2. Timed benchmarking steps
    start_time = time.perf_counter()
    measured_steps = 0
    measured_windows = 0

    for (batch_x,) in dataloader:
        optimizer.zero_grad()
        _, recon = model(batch_x)
        loss = criterion(recon, batch_x)
        loss.backward()
        optimizer.step()
        measured_steps += 1
        measured_windows += batch_x.size(0)

    elapsed_sec = time.perf_counter() - start_time
    ms_per_window = (elapsed_sec / measured_windows) * 1000.0
    sec_per_epoch = (ms_per_window * total_train_windows) / 1000.0
    total_estimated_sec = sec_per_epoch * target_epochs
    total_estimated_hours = total_estimated_sec / 3600.0

    logger.info(f"Timing Results:")
    logger.info(f"  - Measured Windows:    {measured_windows}")
    logger.info(f"  - Step Duration:       {elapsed_sec:.4f} s")
    logger.info(f"  - Latency:             {ms_per_window:.2f} ms/window")
    logger.info(f"  - Est. Epoch Duration: {sec_per_epoch:.2f} s")
    logger.info(f"  - Total ({target_epochs} Epochs): {total_estimated_hours:.3f} hours ({total_estimated_sec:.1f} s)")

    budget_passed = total_estimated_hours <= max_budget_hours
    fallback_selected = "none" if budget_passed else "Step (a): Reduce Sequence Length"

    report = {
        "benchmark_parameters": {
            "slice_size": slice_size,
            "batch_size": batch_size,
            "seq_len": T,
            "channels": C,
            "total_corpus_windows": total_train_windows,
            "target_epochs": target_epochs,
            "device": "CPU"
        },
        "empirical_metrics": {
            "elapsed_seconds": round(elapsed_sec, 4),
            "ms_per_window": round(ms_per_window, 2),
            "estimated_sec_per_epoch": round(sec_per_epoch, 2),
            "total_estimated_hours": round(total_estimated_hours, 4),
            "max_budget_hours": max_budget_hours
        },
        "gate_status": "PASS" if budget_passed else "FAIL",
        "fallback_strategy": fallback_selected,
        "model_parameters_count": sum(p.numel() for p in model.parameters())
    }

    report_path = CHUNK04_DIR / "timing_pilot_report.json"
    CHUNK04_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Timing pilot report written to {report_path}")
    logger.info(f"Compute-Budget Gate Status: {report['gate_status']}")

    assert budget_passed, f"Compute budget exceeded: {total_estimated_hours:.2f}h > {max_budget_hours}h"
    return report


def main() -> None:
    run_timing_pilot()


if __name__ == "__main__":
    main()
