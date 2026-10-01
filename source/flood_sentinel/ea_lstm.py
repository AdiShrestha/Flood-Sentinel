"""Entity-Aware LSTM (EA-LSTM) Architecture (Kratzert et al., 2019; audited migration, no learned weights).

Implements the custom EA-LSTM cell where the input gate is conditioned exclusively
on static catchment attributes. The binary head is a research adaptation;
this is not a replication of the paper's trained rainfall-runoff system.
"""

from typing import Tuple
import torch
import torch.nn as nn
from .validation import positive_int, real_scalar
from .model import _finite_output


class EALSTMCell(nn.Module):
    """Entity-Aware LSTM Cell.

    Input gate is static-conditioned: i = sigmoid(W_i * x_static + b_i)
    Forget, Candidate, Output gates process dynamic temporal forcing.
    """
    def __init__(self, dynamic_dim: int = 6, static_dim: int = 8, hidden_dim: int = 32):
        super().__init__()
        for v in (dynamic_dim, static_dim, hidden_dim): positive_int(v)
        self.dynamic_dim = dynamic_dim
        self.static_dim = static_dim
        self.hidden_dim = hidden_dim

        # Static-conditioned input gate (Kratzert et al., 2019).
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
        tensors = (x_d_t,h_prev,c_prev,i_static)
        if any(x.ndim != 2 or not x.is_floating_point() or not torch.isfinite(x).all() for x in tensors):
            raise ValueError('Finite two-dimensional floating point recurrence inputs required.')
        b = x_d_t.shape[0]
        if b < 1 or x_d_t.shape[1] != self.dynamic_dim or any(x.shape != (b,self.hidden_dim) for x in tensors[1:]):
            raise ValueError('Recurrence state dimension mismatch.')
        if any(x.dtype != x_d_t.dtype or x.device != x_d_t.device for x in tensors[1:]) or ((i_static < 0) | (i_static > 1)).any():
            raise ValueError('Aligned recurrence dtype/device and an input gate in [0,1] required.')
        f_t = torch.sigmoid(self.w_f(x_d_t) + self.u_f(h_prev))
        c_tilde = torch.tanh(self.w_c(x_d_t) + self.u_c(h_prev))
        c_t = f_t * c_prev + i_static * c_tilde
        o_t = torch.sigmoid(self.w_o(x_d_t) + self.u_o(h_prev))
        h_t = o_t * torch.tanh(c_t)
        return _finite_output(h_t), _finite_output(c_t)


class EALSTMModel(nn.Module):
    """EA-LSTM recurrence with an explicitly configured binary logit head."""
    def __init__(self, dynamic_dim: int = 6, static_dim: int = 8, hidden_dim: int = 32,
                 classifier_width: int = 16, dropout: float = .1):
        super().__init__()
        positive_int(classifier_width)
        if not 0 <= real_scalar(dropout) < 1: raise ValueError('Dropout must lie in [0,1).')
        self.hidden_dim = hidden_dim
        self.cell = EALSTMCell(dynamic_dim, static_dim, hidden_dim)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, classifier_width),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(classifier_width, 1)
        )

    def forward(self, x_dynamic: torch.Tensor, x_static: torch.Tensor) -> torch.Tensor:
        """Forward pass across temporal sequence.

        Args:
            x_dynamic: (Batch, Time, configured dynamic channels)
            x_static:  (Batch, configured static channels)

        Returns:
            logits: (Batch,)
        """
        if x_dynamic.ndim != 3 or min(x_dynamic.shape) < 1 or x_static.ndim != 2:
            raise ValueError("Nonempty aligned dynamic and static input tensors are required")
        if x_dynamic.shape[0] != x_static.shape[0] or x_dynamic.shape[2] != self.cell.dynamic_dim or x_static.shape[1] != self.cell.static_dim:
            raise ValueError("EA-LSTM input dimension mismatch")
        if not torch.isfinite(x_dynamic).all() or not torch.isfinite(x_static).all():
            raise ValueError("Missing static/dynamic observations need an explicit upstream policy")
        if not x_dynamic.is_floating_point() or not x_static.is_floating_point() or x_dynamic.dtype != x_static.dtype or x_dynamic.device != x_static.device:
            raise ValueError("Dynamic/static inputs must have a common floating point dtype and device")
        b, t, _ = x_dynamic.size()
        i_static = torch.sigmoid(self.cell.w_i(x_static))

        h_t = x_dynamic.new_zeros(b, self.hidden_dim)
        c_t = x_dynamic.new_zeros(b, self.hidden_dim)

        for step in range(t):
            h_t, c_t = self.cell(x_dynamic[:, step, :], h_t, c_t, i_static)

        logits = self.classifier(h_t).squeeze(-1)
        return _finite_output(logits)
