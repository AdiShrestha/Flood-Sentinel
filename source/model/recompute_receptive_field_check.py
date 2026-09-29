"""Independent Recompute Script for C-ENCODER Causal Receptive Field (C04-02 / INV-020).

Independently evaluates autograd gradient sensitivity without importing test_causal_receptive_field.py.
Outputs single-line JSON matching gatekeeper recompute specification.
"""

import json
import sys
from pathlib import Path

import torch

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.model.c_encoder import CEncoderPretrainModel


def run_independent_recompute() -> None:
    T = 365
    C = 6
    D = 64
    
    model = CEncoderPretrainModel(in_channels=C, d_model=D, tcn_layers=3, transformer_layers=2)
    model.eval()
    
    test_positions = [25, 75, 150, 225, 300]
    max_future_grad = 0.0
    all_causal = True
    
    for tau in test_positions:
        x = torch.randn(1, T, C, requires_grad=True)
        z, x_hat = model(x)
        
        # Loss on query timestep
        loss = z[0, tau, :].sum() + x_hat[0, tau, :].sum()
        loss.backward()
        
        grad = x.grad[0]  # (T, C)
        future_grad = float(torch.norm(grad[tau + 1:, :]).item()) if tau < T - 1 else 0.0
        max_future_grad = max(max_future_grad, future_grad)
        
        if future_grad > 1e-6:
            all_causal = False
            
    result = {
        "causal_isolation_valid": all_causal,
        "max_future_grad": max_future_grad,
        "independent_checks_passed": len(test_positions),
    }
    
    # Must print single line JSON for gatekeeper recompute parser
    print(json.dumps(result))
    if all_causal:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    run_independent_recompute()
