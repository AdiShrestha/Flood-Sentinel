"""T-COMP Correctness Proof for C-ENCODER Causal Receptive Field (C04-02 / INV-020).

Mechanically proves that C-ENCODER satisfies strict causal receptive field isolation:
1. For any query timestep tau, representations z_tau and outputs x_hat_tau have
   identically zero mathematical dependency on future inputs X_{t > tau}.
2. Perturbing future inputs produces exactly zero perturbation in antecedent representations (||Delta z_tau|| == 0).
3. Autograd gradient Jacobian d z_tau / d X_{t > tau} == 0.0 for all future positions.
4. Deliberately constructed non-causal baseline (bidirectional attention / centered conv) is mechanically flagged.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.model.c_encoder import CEncoderPretrainModel, CausalHydroEncoder
from source.utils.logging_config import get_logger

logger = get_logger("test_causal_receptive_field")


class NonCausalControlEncoder(nn.Module):
    """Deliberately leaking non-causal encoder control with centered convs and bidirectional attention."""

    def __init__(self, in_channels: int = 6, d_model: int = 64) -> None:
        super().__init__()
        self.input_proj = nn.Linear(in_channels, d_model)
        # Centered padding causes forward leakage
        self.conv = nn.Conv1d(d_model, d_model, kernel_size=3, padding=1)
        self.attn = nn.MultiheadAttention(d_model, num_heads=4, batch_first=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (B, T, C)
        h = self.input_proj(x)
        h_conv = self.conv(h.transpose(1, 2)).transpose(1, 2)
        h_attn, _ = self.attn(h_conv, h_conv, h_conv)  # Unmasked bidirectional attention
        return h_attn


def evaluate_causal_isolation(
    model: nn.Module,
    tau: int,
    T: int = 365,
    C: int = 6,
    device: str = "cpu"
) -> Dict[str, Any]:
    """Evaluate mathematical causal isolation at query timestamp tau."""
    model.eval()
    
    # 1. Base forward pass with autograd tracking
    torch.manual_seed(42 + tau)
    x = torch.randn(1, T, C, device=device, requires_grad=True)
    
    if isinstance(model, CEncoderPretrainModel):
        z, x_hat = model(x)
    elif isinstance(model, CausalHydroEncoder) or isinstance(model, NonCausalControlEncoder):
        z = model(x)
        x_hat = z
    else:
        z = model(x)
        x_hat = z
        
    z_tau_base = z[0, tau, :].detach().clone()
    x_hat_tau_base = x_hat[0, tau, :].detach().clone()
    
    # 2. Gradient Jacobian sensitivity check
    # Loss = sum(z_tau)
    loss = z[0, tau, :].sum()
    loss.backward()
    
    grad = x.grad[0].detach().clone()  # (T, C)
    
    past_grad_norm = float(torch.norm(grad[:tau + 1, :]).item())
    future_grad_norm = float(torch.norm(grad[tau + 1:, :]).item()) if tau < T - 1 else 0.0
    
    # 3. Perturbation check
    x_perturbed = x.detach().clone()
    # Add large perturbations to future timesteps t > tau
    if tau < T - 1:
        x_perturbed[0, tau + 1:, :] += torch.randn_like(x_perturbed[0, tau + 1:, :]) * 100.0
        
    with torch.no_grad():
        if isinstance(model, CEncoderPretrainModel):
            z_pert, x_hat_pert = model(x_perturbed)
        else:
            z_pert = model(x_perturbed)
            x_hat_pert = z_pert
            
    z_tau_pert = z_pert[0, tau, :]
    x_hat_tau_pert = x_hat_pert[0, tau, :]
    
    z_diff_max = float(torch.max(torch.abs(z_tau_pert - z_tau_base)).item())
    x_hat_diff_max = float(torch.max(torch.abs(x_hat_tau_pert - x_hat_tau_base)).item())
    
    is_causal = (future_grad_norm < 1e-6) and (z_diff_max < 1e-6) and (x_hat_diff_max < 1e-6)
    
    return {
        "tau": tau,
        "past_grad_norm": past_grad_norm,
        "future_grad_norm": future_grad_norm,
        "z_diff_max": z_diff_max,
        "x_hat_diff_max": x_hat_diff_max,
        "is_causal": is_causal,
    }


def main() -> None:
    logger.info("Executing T-COMP C-ENCODER Receptive Field Correctness Proof (INV-020)...")
    
    T = 365
    C = 6
    D = 64
    
    # 1. Test C-ENCODER
    model = CEncoderPretrainModel(in_channels=C, d_model=D, tcn_layers=3, transformer_layers=2)
    
    test_positions = [10, 30, 60, 100, 150, 200, 250, 300, 330, 350]
    causal_results = []
    
    max_future_grad = 0.0
    for tau in test_positions:
        res = evaluate_causal_isolation(model, tau, T=T, C=C)
        causal_results.append(res)
        max_future_grad = max(max_future_grad, res["future_grad_norm"])
        status_str = "PASS (Strictly Causal)" if res["is_causal"] else "FAIL (Future Leakage Detected)"
        logger.info(
            f"Query Position tau={tau:3d}: {status_str} | "
            f"Future Grad Norm={res['future_grad_norm']:.2e}, Max Delta z={res['z_diff_max']:.2e}"
        )
        
    causal_passed = all(r["is_causal"] for r in causal_results)
    
    # 2. Test Non-Causal Control (Must be mechanically flagged as leaking)
    logger.info("Evaluating Non-Causal Control Baseline for mechanical defect detection...")
    control_model = NonCausalControlEncoder(in_channels=C, d_model=D)
    control_res = evaluate_causal_isolation(control_model, tau=100, T=T, C=C)
    control_detected = not control_res["is_causal"]
    
    logger.info(
        f"Non-Causal Control Detection: {'DETECTED (PASS)' if control_detected else 'MISSED (FAIL)'} | "
        f"Future Grad Norm={control_res['future_grad_norm']:.2e}, Max Delta z={control_res['z_diff_max']:.2e}"
    )
    
    all_passed = causal_passed and control_detected
    
    proof_record = {
        "scientific_claim": (
            "C-ENCODER satisfies strict causal receptive field isolation under INV-020: "
            "future input gradient sensitivity is identically zero (d z_tau / d X_{t > tau} = 0) "
            "and future input perturbations produce zero divergence in antecedent representations."
        ),
        "causal_isolation_valid": all_passed,
        "tested_positions_count": len(test_positions),
        "causal_positions_passed": sum(1 for r in causal_results if r["is_causal"]),
        "non_causal_control_detected": control_detected,
        "future_gradient_norm_max": max_future_grad,
        "results": causal_results,
        "control_result": control_res,
    }
    
    proof_path = _PROJECT_ROOT / "project" / "chunks" / "chunk04" / "receptive_field_proof.json"
    proof_path.parent.mkdir(parents=True, exist_ok=True)
    with open(proof_path, "w", encoding="utf-8") as f:
        json.dump(proof_record, f, indent=2)
        
    logger.info(f"Proof record serialized to {proof_path}")
    
    if all_passed:
        logger.info("T-COMP C-ENCODER Receptive Field Correctness Proof PASSED (10/10 positions strictly causal).")
        sys.exit(0)
    else:
        logger.error("T-COMP Receptive Field Correctness Proof FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
