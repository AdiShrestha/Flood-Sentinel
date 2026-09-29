"""Entity-Aware LSTM (EA-LSTM) Architecture (Kratzert et al., 2019 / C06-04).

Implements the custom EA-LSTM cell where the input gate is conditioned exclusively
on static catchment attributes, modulating dynamical recurrence for multi-basin flood prediction.
"""

from typing import Tuple
import torch
import torch.nn as nn


class EALSTMCell(nn.Module):
    """Entity-Aware LSTM Cell.

    Input gate is static-conditioned: i = sigmoid(W_i * x_static + b_i)
    Forget, Candidate, Output gates process dynamic temporal forcing.
    """
    def __init__(self, dynamic_dim: int = 6, static_dim: int = 8, hidden_dim: int = 32):
        super().__init__()
        self.dynamic_dim = dynamic_dim
        self.static_dim = static_dim
        self.hidden_dim = hidden_dim

        # Static input gate projection (Kratzert et al. 2019, Eq. 5)
        self.w_i = nn.Linear(static_dim, hidden_dim)

        # Dynamic gates projections
        self.w_f = nn.Linear(dynamic_dim, hidden_dim)
        self.u_f = nn.Linear(hidden_dim, hidden_dim, bias=False)

        self.w_c = nn.Linear(dynamic_dim, hidden_dim)
        self.u_c = nn.Linear(hidden_dim, hidden_dim, bias=False)

        self.w_o = nn.Linear(dynamic_dim, hidden_dim)
        self.u_o = nn.Linear(hidden_dim, hidden_dim, bias=False)

    def forward(
        self,
        x_d_t: torch.Tensor,
        h_prev: torch.Tensor,
        c_prev: torch.Tensor,
        i_static: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Single recurrence step."""
        f_t = torch.sigmoid(self.w_f(x_d_t) + self.u_f(h_prev))
        c_tilde = torch.tanh(self.w_c(x_d_t) + self.u_c(h_prev))
        c_t = f_t * c_prev + i_static * c_tilde
        o_t = torch.sigmoid(self.w_o(x_d_t) + self.u_o(h_prev))
        h_t = o_t * torch.tanh(c_t)
        return h_t, c_t


class EALSTMModel(nn.Module):
    """Full Entity-Aware LSTM sequential network for flood event prediction."""
    def __init__(self, dynamic_dim: int = 6, static_dim: int = 8, hidden_dim: int = 32):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.cell = EALSTMCell(dynamic_dim, static_dim, hidden_dim)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, 16),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(16, 1)
        )

    def forward(self, x_dynamic: torch.Tensor, x_static: torch.Tensor) -> torch.Tensor:
        """Forward pass across temporal sequence.

        Args:
            x_dynamic: (Batch, Time=365, Channels=6)
            x_static:  (Batch, StaticChannels=8)

        Returns:
            logits: (Batch,)
        """
        b, t, _ = x_dynamic.size()
        i_static = torch.sigmoid(self.cell.w_i(x_static))

        h_t = torch.zeros(b, self.hidden_dim, device=x_dynamic.device)
        c_t = torch.zeros(b, self.hidden_dim, device=x_dynamic.device)

        for step in range(t):
            h_t, c_t = self.cell(x_dynamic[:, step, :], h_t, c_t, i_static)

        logits = self.classifier(h_t).squeeze(-1)
        return logits
