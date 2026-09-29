"""Self-Supervised Pretraining Engine for C-ENCODER (C04-05 / FR-009 / NFR-001).

Executes masked temporal reconstruction pretraining across training windows:
1. Loads HydroPretrainDataset with dynamic 15% temporal masking.
2. Optimizes Masked MSE loss using AdamW and CosineAnnealingLR.
3. Checkpoints trained model weights and logs pretraining metrics to pretraining_summary.json.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.model.c_encoder import CEncoderPretrainModel
from source.model.pretrain_dataset import HydroPretrainDataset
from source.utils.config import CHUNK04_DIR
from source.utils.logging_config import get_logger

logger = get_logger("pretrain_encoder")


def masked_mse_loss(x_hat: torch.Tensor, x_target: torch.Tensor, mask: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    """Compute MSE loss exclusively on masked elements."""
    diff_sq = ((x_hat - x_target) * mask) ** 2
    loss = diff_sq.sum() / (mask.sum() + eps)
    return loss


def train_encoder(
    epochs: int = 5,
    batch_size: int = 64,
    lr: float = 1e-3,
    weight_decay: float = 0.01,
    test_run: bool = False,
    max_samples: int = None
) -> Dict[str, Any]:
    """Execute pretraining loop for C-ENCODER."""
    start_time = time.perf_counter()
    logger.info(f"Starting C-ENCODER Self-Supervised Pretraining (Epochs: {epochs}, Batch Size: {batch_size}, Test Run: {test_run})...")

    sample_limit = 256 if test_run and max_samples is None else max_samples
    dataset = HydroPretrainDataset(max_samples=sample_limit, precache=True)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, drop_last=False)
    logger.info(f"Pretraining dataset initialized with {len(dataset)} windows ({len(dataloader)} batches/epoch).")

    device = torch.device("cpu")
    model = CEncoderPretrainModel(
        in_channels=6,
        d_model=64,
        tcn_layers=3,
        transformer_layers=2,
        n_heads=4,
        d_ff=128,
        dropout=0.1
    ).to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)

    history: List[Dict[str, Any]] = []

    for epoch in range(1, epochs + 1):
        epoch_start = time.perf_counter()
        model.train()
        total_loss = 0.0
        total_batches = 0

        for batch_idx, (x_masked, x_target, mask) in enumerate(dataloader):
            x_masked = x_masked.to(device)
            x_target = x_target.to(device)
            mask = mask.to(device)

            optimizer.zero_grad()
            _, x_hat = model(x_masked)
            loss = masked_mse_loss(x_hat, x_target, mask)
            loss.backward()

            # Gradient clipping for numerical stability
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            total_loss += loss.item()
            total_batches += 1

        scheduler.step()
        epoch_duration = time.perf_counter() - epoch_start
        avg_loss = total_loss / max(1, total_batches)
        current_lr = scheduler.get_last_lr()[0]

        logger.info(f"Epoch [{epoch:02d}/{epochs:02d}] - Loss: {avg_loss:.5f} - LR: {current_lr:.6f} - Duration: {epoch_duration:.2f}s")
        history.append({
            "epoch": epoch,
            "loss": round(avg_loss, 6),
            "lr": round(current_lr, 7),
            "duration_sec": round(epoch_duration, 3)
        })

    total_wallclock_sec = time.perf_counter() - start_time
    total_params = sum(p.numel() for p in model.parameters())

    # 1. Save checkpoint
    checkpoint_dir = CHUNK04_DIR / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_dir / "c_encoder_pretrained.pt"

    checkpoint_dict = {
        "model_state_dict": model.state_dict(),
        "encoder_state_dict": model.encoder.state_dict(),
        "head_state_dict": model.head.state_dict(),
        "model_hyperparameters": {
            "in_channels": 6,
            "d_model": 64,
            "tcn_layers": 3,
            "transformer_layers": 2,
            "n_heads": 4,
            "d_ff": 128,
            "dropout": 0.1
        },
        "training_metadata": {
            "epochs": epochs,
            "batch_size": batch_size,
            "final_loss": history[-1]["loss"] if history else None,
            "total_wallclock_sec": round(total_wallclock_sec, 2),
            "total_params": total_params
        }
    }
    torch.save(checkpoint_dict, checkpoint_path)
    logger.info(f"Model checkpoint successfully saved to {checkpoint_path}")

    # 2. Save pretraining summary JSON
    summary = {
        "model_architecture": "C-ENCODER (Dilated Causal TCN + Causal Transformer)",
        "total_parameters": total_params,
        "epochs_completed": epochs,
        "batch_size": batch_size,
        "dataset_windows_used": len(dataset),
        "final_training_loss": history[-1]["loss"] if history else None,
        "initial_training_loss": history[0]["loss"] if history else None,
        "loss_reduction_pct": round(((history[0]["loss"] - history[-1]["loss"]) / history[0]["loss"]) * 100, 2) if history and history[0]["loss"] > 0 else 0.0,
        "total_wallclock_seconds": round(total_wallclock_sec, 2),
        "history": history,
        "checkpoint_file": str(checkpoint_path.relative_to(_PROJECT_ROOT))
    }

    summary_path = CHUNK04_DIR / "pretraining_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Pretraining summary written to {summary_path}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Pretrain C-ENCODER with Masked Temporal Reconstruction")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--test-run", action="store_true", help="Run fast test slice")
    args = parser.parse_args()

    train_encoder(epochs=args.epochs, batch_size=args.batch_size, lr=args.lr, test_run=args.test_run)


if __name__ == "__main__":
    main()
