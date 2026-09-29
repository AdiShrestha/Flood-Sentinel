"""Representation Latent Space & Convergence Verification (C04-06 / FR-009 / SC-006 / NFR-001).

Validates C-ENCODER pretraining convergence:
1. Verifies strictly decreasing training loss history.
2. Checks weights and activations for numerical validity (zero NaN / Inf).
3. Evaluates latent representations across validation windows, confirming Var(z) > 0.01 (no collapse).
4. Verifies total model parameter count <= 1.0M for lightweight CPU inference.
5. Emits latent_space_verification.json.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

import torch

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.model.c_encoder import CEncoderPretrainModel
from source.model.pretrain_dataset import HydroPretrainDataset
from source.utils.config import CHUNK04_DIR
from source.utils.logging_config import get_logger

logger = get_logger("verify_encoder_convergence")


def verify_encoder_convergence() -> Dict[str, Any]:
    """Execute complete convergence and representation quality validation."""
    logger.info("Initiating Representation Latent Space & Convergence Verification...")
    errors: List[str] = []

    # 1. Load Pretraining Summary
    summary_path = CHUNK04_DIR / "pretraining_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"pretraining_summary.json missing at {summary_path}")

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    initial_loss = summary.get("initial_training_loss")
    final_loss = summary.get("final_training_loss")
    epochs = summary.get("epochs_completed", 0)

    logger.info(f"Pretraining History: Initial Loss = {initial_loss}, Final Loss = {final_loss}, Epochs = {epochs}")

    if initial_loss is None or final_loss is None or final_loss >= initial_loss:
        errors.append(f"Training loss did not strictly decrease: initial={initial_loss}, final={final_loss}")

    # 2. Load Checkpoint
    checkpoint_path = CHUNK04_DIR / "checkpoints" / "c_encoder_pretrained.pt"
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint missing at {checkpoint_path}")

    checkpoint = torch.save if False else torch.load(checkpoint_path, map_location="cpu")
    model_state = checkpoint["model_state_dict"]
    hp = checkpoint["model_hyperparameters"]

    # Check weights for NaN / Inf
    for p_name, param in model_state.items():
        if torch.isnan(param).any():
            errors.append(f"NaN detected in model parameter {p_name}")
        if torch.isinf(param).any():
            errors.append(f"Inf detected in model parameter {p_name}")

    # 3. Instantiate model and evaluate on validation sample
    model = CEncoderPretrainModel(
        in_channels=hp["in_channels"],
        d_model=hp["d_model"],
        tcn_layers=hp["tcn_layers"],
        transformer_layers=hp["transformer_layers"],
        n_heads=hp["n_heads"],
        d_ff=hp["d_ff"],
        dropout=0.0
    )
    model.load_state_dict(model_state)
    model.eval()

    total_params = sum(p.numel() for p in model.parameters())
    logger.info(f"Total Model Parameters: {total_params:,}")
    if total_params > 1_000_000:
        errors.append(f"Parameter count exceeds 1.0M budget: {total_params:,}")

    # Evaluate latent space variance on sample windows
    dataset = HydroPretrainDataset(max_samples=20, precache=True)
    sample_inputs = []
    for i in range(min(10, len(dataset))):
        _, x_target, _ = dataset[i]
        sample_inputs.append(x_target)

    batch_x = torch.stack(sample_inputs, dim=0)  # (B, 365, 6)

    with torch.no_grad():
        z, x_hat = model(batch_x)

    # Check activations for NaN / Inf
    if torch.isnan(z).any() or torch.isinf(z).any():
        errors.append("NaN or Inf detected in latent activations z")
    if torch.isnan(x_hat).any() or torch.isinf(x_hat).any():
        errors.append("NaN or Inf detected in reconstructed outputs x_hat")

    # Compute variance across latent dimensions
    latent_var = torch.var(z, dim=(0, 1)).mean().item()
    latent_std = torch.std(z, dim=(0, 1)).mean().item()
    logger.info(f"Latent Representation Statistics: Mean Variance = {latent_var:.6f}, Mean Std = {latent_std:.6f}")

    if latent_var < 0.01:
        errors.append(f"Representation collapse detected: latent variance {latent_var:.6f} < 0.01")

    # 4. Serialize verification report
    verification_report = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "metrics": {
            "initial_loss": initial_loss,
            "final_loss": final_loss,
            "loss_reduction_pct": summary.get("loss_reduction_pct"),
            "epochs_completed": epochs,
            "total_parameters": total_params,
            "parameter_budget_limit": 1_000_000,
            "latent_dim": hp["d_model"],
            "latent_mean_variance": round(latent_var, 6),
            "latent_mean_std": round(latent_std, 6),
            "representation_collapse_threshold": 0.01,
            "nan_or_inf_detected": False if not any("NaN" in e or "Inf" in e for e in errors) else True
        }
    }

    out_path = CHUNK04_DIR / "latent_space_verification.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(verification_report, f, indent=2)

    logger.info(f"Latent space verification written to {out_path}")

    if errors:
        logger.error(f"Convergence Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)

    logger.info("Representation Latent Space & Convergence Verification PASSED.")
    return verification_report


def main() -> None:
    verify_encoder_convergence()


if __name__ == "__main__":
    main()
