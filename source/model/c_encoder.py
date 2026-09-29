"""C-ENCODER: Causal Hybrid Dilated TCN - Transformer Architecture (C04-01 / FR-009 / INV-020).

Implements the neural temporal encoder for Flood Sentinel:
1. CausalConv1d: 1D convolution with asymmetric left-only padding ensuring no forward leakage.
2. DilatedCausalTCNBlock: Residual dilated convolution stack capturing multi-scale antecedent lags.
3. CausalMultiHeadAttention: Multi-head attention with strict lower-triangular causal attention mask.
4. CausalTransformerBlock: Pre-LayerNorm transformer layer with residual feedforward networks.
5. CausalHydroEncoder: Full hybrid encoder mapping (B, T, C_in) -> (B, T, D_latent).
6. MaskedReconstructionHead: Projection head mapping latent states z -> reconstructed observations x_hat.
"""

import math
import sys
from pathlib import Path
from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.logging_config import get_logger

logger = get_logger("c_encoder")


class CausalConv1d(nn.Module):
    """1D Convolution with explicit left-only padding to prevent forward temporal leakage (INV-020)."""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        dilation: int = 1,
        groups: int = 1,
        bias: bool = True
    ) -> None:
        super().__init__()
        self.kernel_size = kernel_size
        self.dilation = dilation
        self.padding = (kernel_size - 1) * dilation
        self.conv = nn.Conv1d(
            in_channels=in_channels,
            out_channels=out_channels,
            kernel_size=kernel_size,
            dilation=dilation,
            groups=groups,
            bias=bias,
            padding=0  # Manual padding applied in forward
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (B, C, T)
        # Pad left side only with (self.padding, 0)
        if self.padding > 0:
            x = F.pad(x, (self.padding, 0))
        return self.conv(x)


class DilatedCausalTCNBlock(nn.Module):
    """Residual Dilated Causal TCN block with LayerNorm and GELU."""

    def __init__(
        self,
        channels: int,
        kernel_size: int = 3,
        dilation: int = 1,
        dropout: float = 0.1
    ) -> None:
        super().__init__()
        self.conv1 = CausalConv1d(channels, channels, kernel_size, dilation=dilation)
        self.norm1 = nn.LayerNorm(channels)
        self.conv2 = CausalConv1d(channels, channels, kernel_size, dilation=dilation)
        self.norm2 = nn.LayerNorm(channels)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (B, T, C)
        residual = x
        
        # Conv 1
        h = x.transpose(1, 2)  # (B, C, T)
        h = self.conv1(h).transpose(1, 2)  # (B, T, C)
        h = self.norm1(h)
        h = self.act(h)
        h = self.dropout(h)

        # Conv 2
        h = h.transpose(1, 2)
        h = self.conv2(h).transpose(1, 2)
        h = self.norm2(h)
        h = self.act(h)
        h = self.dropout(h)

        return residual + h


class CausalMultiHeadAttention(nn.Module):
    """Multi-head self-attention with strict lower-triangular causal masking (INV-020)."""

    def __init__(self, d_model: int, n_heads: int = 4, dropout: float = 0.1) -> None:
        super().__init__()
        assert d_model % n_heads == 0, f"d_model ({d_model}) must be divisible by n_heads ({n_heads})"
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_head = d_model // n_heads
        self.scale = 1.0 / math.sqrt(self.d_head)

        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        # x shape: (B, T, D)
        B, T, D = x.shape

        q = self.q_proj(x).view(B, T, self.n_heads, self.d_head).transpose(1, 2)  # (B, H, T, d_head)
        k = self.k_proj(x).view(B, T, self.n_heads, self.d_head).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.n_heads, self.d_head).transpose(1, 2)

        # Attention scores
        scores = torch.matmul(q, k.transpose(-2, -1)) * self.scale  # (B, H, T, T)

        # Apply causal mask: mask[i, j] = 1 if j <= i else 0
        causal_mask = torch.tril(torch.ones(T, T, device=x.device, dtype=torch.bool))  # (T, T)
        scores = scores.masked_fill(~causal_mask.unsqueeze(0).unsqueeze(0), float("-inf"))

        if mask is not None:
            # Additional external key padding mask if provided
            scores = scores.masked_fill(~mask.unsqueeze(1).unsqueeze(2), float("-inf"))

        attn = F.softmax(scores, dim=-1)
        # In case all elements are masked (e.g. padding), replace NaN with 0
        attn = torch.nan_to_num(attn, nan=0.0)
        attn = self.dropout(attn)

        out = torch.matmul(attn, v)  # (B, H, T, d_head)
        out = out.transpose(1, 2).contiguous().view(B, T, D)
        return self.out_proj(out)


class CausalTransformerBlock(nn.Module):
    """Pre-LayerNorm Causal Transformer block with MLP."""

    def __init__(self, d_model: int, n_heads: int = 4, d_ff: int = 256, dropout: float = 0.1) -> None:
        super().__init__()
        self.norm1 = nn.LayerNorm(d_model)
        self.attn = CausalMultiHeadAttention(d_model, n_heads=n_heads, dropout=dropout)
        self.norm2 = nn.LayerNorm(d_model)
        self.mlp = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Pre-LN Self Attention
        h = self.attn(self.norm1(x))
        x = x + h
        # Pre-LN MLP
        h = self.mlp(self.norm2(x))
        x = x + h
        return x


class CausalHydroEncoder(nn.Module):
    """C-ENCODER: Hybrid Dilated Causal TCN + Transformer Encoder."""

    def __init__(
        self,
        in_channels: int = 6,
        d_model: int = 64,
        tcn_layers: int = 3,
        transformer_layers: int = 2,
        n_heads: int = 4,
        d_ff: int = 128,
        dropout: float = 0.1
    ) -> None:
        super().__init__()
        self.in_channels = in_channels
        self.d_model = d_model

        # Input linear projection
        self.input_proj = nn.Linear(in_channels, d_model)

        # Dilated Causal TCN stack (dilations 1, 2, 4, ...)
        self.tcn_blocks = nn.ModuleList([
            DilatedCausalTCNBlock(d_model, kernel_size=3, dilation=2**i, dropout=dropout)
            for i in range(tcn_layers)
        ])

        # Causal Transformer stack
        self.transformer_blocks = nn.ModuleList([
            CausalTransformerBlock(d_model, n_heads=n_heads, d_ff=d_ff, dropout=dropout)
            for i in range(transformer_layers)
        ])

        self.final_norm = nn.LayerNorm(d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (B, T, C_in)
        h = self.input_proj(x)  # (B, T, D)

        # Apply TCN blocks
        for block in self.tcn_blocks:
            h = block(h)

        # Apply Transformer blocks
        for block in self.transformer_blocks:
            h = block(h)

        return self.final_norm(h)  # (B, T, D)


class MaskedReconstructionHead(nn.Module):
    """Self-supervised masked reconstruction projection head."""

    def __init__(self, d_model: int = 64, out_channels: int = 6) -> None:
        super().__init__()
        self.proj = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.Linear(d_model, out_channels)
        )

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        # z shape: (B, T, D) -> x_hat shape: (B, T, C_out)
        return self.proj(z)


class CEncoderPretrainModel(nn.Module):
    """Full self-supervised pretraining model (Encoder + Reconstruction Head)."""

    def __init__(
        self,
        in_channels: int = 6,
        d_model: int = 64,
        tcn_layers: int = 3,
        transformer_layers: int = 2,
        n_heads: int = 4,
        d_ff: int = 128,
        dropout: float = 0.1
    ) -> None:
        super().__init__()
        self.encoder = CausalHydroEncoder(
            in_channels=in_channels,
            d_model=d_model,
            tcn_layers=tcn_layers,
            transformer_layers=transformer_layers,
            n_heads=n_heads,
            d_ff=d_ff,
            dropout=dropout
        )
        self.head = MaskedReconstructionHead(d_model=d_model, out_channels=in_channels)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # x shape: (B, T, C)
        z = self.encoder(x)  # (B, T, D)
        x_hat = self.head(z)  # (B, T, C)
        return z, x_hat


def main() -> None:
    logger.info("Executing C-ENCODER Architecture Validation...")
    B, T, C, D = 2, 365, 6, 64
    x = torch.randn(B, T, C)

    model = CEncoderPretrainModel(in_channels=C, d_model=D, tcn_layers=3, transformer_layers=2)
    model.eval()

    with torch.no_grad():
        z, x_hat = model(x)

    logger.info(f"Input Shape:  {x.shape}")
    logger.info(f"Latent Shape: {z.shape} (Expected: ({B}, {T}, {D}))")
    logger.info(f"Recon Shape:  {x_hat.shape} (Expected: ({B}, {T}, {C}))")

    assert z.shape == (B, T, D), f"Latent shape mismatch: {z.shape} vs ({B}, {T}, {D})"
    assert x_hat.shape == (B, T, C), f"Recon shape mismatch: {x_hat.shape} vs ({B}, {T}, {C})"

    num_params = sum(p.numel() for p in model.parameters())
    logger.info(f"Total C-ENCODER Parameters: {num_params:,}")
    logger.info("C-ENCODER Architecture Validation PASSED.")


if __name__ == "__main__":
    main()
