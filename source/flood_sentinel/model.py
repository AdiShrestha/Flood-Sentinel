"""Migrated causal neural operators; no checkpoints or legacy data are loaded.

Temporal causality is a code property, not an assurance of data availability.
"""
import math
from typing import Optional, Tuple
import torch
from torch import nn
from torch.nn import functional as F
from .validation import positive_int, real_scalar


def _dropout(value):
    if not 0 <= real_scalar(value) < 1: raise ValueError('Dropout must lie in [0,1).')


def _tensor(x, channels, *, channel_first=False):
    axis = 1 if channel_first else 2
    if not isinstance(x, torch.Tensor) or x.ndim != 3 or min(x.shape) < 1 or x.shape[axis] != channels:
        raise ValueError('Nonempty aligned three-dimensional neural input required.')
    if not x.is_floating_point() or not torch.isfinite(x).all():
        raise ValueError('Finite floating point neural inputs required.')


def _finite_output(x):
    if not torch.isfinite(x).all(): raise ValueError('Nonfinite neural output; investigate inputs, weights and arithmetic.')
    return x

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
        for v in (in_channels, out_channels, kernel_size, dilation, groups): positive_int(v)
        if type(bias) is not bool or in_channels % groups or out_channels % groups:
            raise ValueError('Invalid convolution groups or bias flag.')
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
        _tensor(x, self.conv.in_channels, channel_first=True)
        if self.padding > 0:
            x = F.pad(x, (self.padding, 0))
        return _finite_output(self.conv(x))

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
        positive_int(channels, minimum=2)
        _dropout(dropout)
        self.conv1 = CausalConv1d(channels, channels, kernel_size, dilation=dilation)
        self.norm1 = nn.LayerNorm(channels)
        self.conv2 = CausalConv1d(channels, channels, kernel_size, dilation=dilation)
        self.norm2 = nn.LayerNorm(channels)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (B, T, C)
        _tensor(x, self.conv1.conv.in_channels)
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

        return _finite_output(residual + h)

class CausalMultiHeadAttention(nn.Module):
    """Self-attention with an inclusive causal mask: each step can attend to itself and its past."""

    def __init__(self, d_model: int, n_heads: int = 4, dropout: float = 0.1) -> None:
        super().__init__()
        positive_int(d_model)
        _dropout(dropout)
        if type(n_heads) is not int or n_heads < 1 or d_model < 1 or d_model % n_heads:
            raise ValueError("d_model must be positive and divisible by a positive n_heads")
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
        _tensor(x, self.d_model)
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
            if mask.dtype != torch.bool or mask.shape != (B, T) or mask.device != x.device:
                raise ValueError("Key validity mask must be boolean with shape (batch, time)")
            # Additional external key padding mask if provided
            scores = scores.masked_fill(~mask.unsqueeze(1).unsqueeze(2), float("-inf"))

        attn = F.softmax(scores, dim=-1)
        if not torch.isfinite(attn).all():
            raise ValueError("Attention has no valid key or contains nonfinite scores; no NaN replacement.")
        attn = self.dropout(attn)

        out = torch.matmul(attn, v)  # (B, H, T, d_head)
        out = out.transpose(1, 2).contiguous().view(B, T, D)
        return _finite_output(self.out_proj(out))

class CausalTransformerBlock(nn.Module):
    """Pre-LayerNorm Causal Transformer block with MLP."""

    def __init__(self, d_model: int, n_heads: int = 4, d_ff: int = 256, dropout: float = 0.1) -> None:
        super().__init__()
        positive_int(d_model, minimum=2)
        positive_int(d_ff)
        _dropout(dropout)
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
        return _finite_output(x)

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
        if any(type(v) is not int or v < 0 for v in (tcn_layers, transformer_layers)):
            raise ValueError("Layer counts must be nonnegative integers")
        positive_int(in_channels)
        positive_int(d_model, minimum=2)
        positive_int(n_heads)
        positive_int(d_ff)
        _dropout(dropout)
        if d_model % n_heads: raise ValueError('d_model must be divisible by n_heads.')
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
        _tensor(x, self.in_channels)
        h = self.input_proj(x)  # (B, T, D)

        # Apply TCN blocks
        for block in self.tcn_blocks:
            h = block(h)

        # Apply Transformer blocks
        for block in self.transformer_blocks:
            h = block(h)

        return _finite_output(self.final_norm(h))  # (B, T, D)

class MaskedReconstructionHead(nn.Module):
    """Self-supervised masked reconstruction projection head."""

    def __init__(self, d_model: int = 64, out_channels: int = 6) -> None:
        super().__init__()
        positive_int(d_model)
        positive_int(out_channels)
        self.proj = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.Linear(d_model, out_channels)
        )

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        # z shape: (B, T, D) -> x_hat shape: (B, T, C_out)
        _tensor(z, self.proj[0].in_features)
        return _finite_output(self.proj(z))
