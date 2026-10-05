"""Observed-only masked objective and deterministic target-withheld scoring."""
import torch
from torch import nn
from .model import CausalHydroEncoder, MaskedReconstructionHead


class MaskedHydroModel(nn.Module):
    """Input includes one visible-observation indicator per physical channel.

    This changes the legacy model's input dimension; old checkpoints are incompatible.
    """
    def __init__(self, physical_channels: int, **encoder_config):
        super().__init__()
        if type(physical_channels) is not int or physical_channels < 1:
            raise ValueError('physical_channels must be positive.')
        self.physical_channels = physical_channels
        self.encoder = CausalHydroEncoder(in_channels=2*physical_channels, **encoder_config)
        self.head = MaskedReconstructionHead(self.encoder.d_model, physical_channels)

    def forward(self, values, visible):
        if values.ndim != 3 or values.shape[-1] != self.physical_channels:
            raise ValueError('Expected (batch, time, physical_channels).')
        if visible.shape != values.shape or visible.dtype != torch.bool or visible.device != values.device:
            raise ValueError('Visible-observation mask must be boolean and aligned.')
        if not values.is_floating_point() or not torch.isfinite(values).all():
            raise ValueError('Provide finite normalized values and an explicit observed mask.')
        masked = torch.where(visible, values, torch.zeros_like(values))
        inputs = torch.cat((masked, visible.to(values.dtype)), dim=-1)
        z = self.encoder(inputs)
        return z, self.head(z)

    def masked_loss(self, values, observed, hidden):
        """Bind training masks to the actual encoder input and the observed-only loss.

        Standalone loss arithmetic cannot establish that its targets were withheld.
        Use this method for reconstruction training; save the real mask policy and
        training trace separately. This objective does not train a future flood target.
        """
        if observed.shape != values.shape or hidden.shape != values.shape or observed.dtype != torch.bool or hidden.dtype != torch.bool:
            raise ValueError('Boolean aligned training masks required.')
        if observed.device != values.device or hidden.device != values.device:
            raise ValueError('Training masks and values must share a device.')
        if (hidden & ~observed).any(): raise ValueError('Training must not select missing values as targets.')
        if not hidden.any(): raise ValueError('No withheld training targets.')
        _, prediction = self(values, observed & ~hidden)
        return masked_observed_mse(prediction, values.detach(), hidden, observed)


def masked_observed_mse(prediction, target, hidden, observed):
    """Observed-only MSE arithmetic; use model.masked_loss to bind input withholding."""
    if not (prediction.shape == target.shape == hidden.shape == observed.shape):
        raise ValueError('Loss tensors must be aligned.')
    if hidden.dtype != torch.bool or observed.dtype != torch.bool:
        raise ValueError('Loss masks must be boolean.')
    if not prediction.is_floating_point() or not target.is_floating_point() or any(t.device != prediction.device for t in (target,hidden,observed)):
        raise ValueError('Floating targets/predictions and a common device required.')
    valid = hidden & observed
    if not valid.any(): raise ValueError('No observed withheld targets; do not produce a zero loss.')
    if not torch.isfinite(prediction[valid]).all() or not torch.isfinite(target[valid]).all():
        raise ValueError('Nonfinite observed targets/predictions.')
    loss = (prediction[valid] - target[valid]).square().mean()
    if not torch.isfinite(loss): raise ValueError('Squared-error overflow; do not return an infinite objective.')
    return loss


@torch.no_grad()
def leave_channel_out_score(model: MaskedHydroModel, values, observed):
    """Cross-channel reconstruction MSE per time; each target channel is withheld.

    Use a compatible preregistered training mask distribution. This is not a
    forecast score or a probability, and no flood-skill claim is made here.
    """
    if model.training: raise ValueError('Scoring requires eval mode.')
    if observed.shape != values.shape or observed.dtype != torch.bool:
        raise ValueError('Observed mask must align with values.')
    if not observed.any(dim=-1).all(): raise ValueError('A time step has no observed scoring target.')
    errors = torch.zeros_like(values)
    for channel in range(model.physical_channels):
        visible = observed.clone(); visible[..., channel] = False
        _, reconstruction = model(values, visible)
        errors[..., channel] = (reconstruction[..., channel] - values[..., channel]).square()
    result = torch.where(observed, errors, torch.zeros_like(errors)).sum(dim=-1) / observed.sum(dim=-1)
    if not torch.isfinite(result).all(): raise ValueError('Nonfinite reconstruction scores.')
    return result


from dataclasses import dataclass
from typing import Any, Optional, Sequence
import numpy as np
from .scoring import LatentReference
from .validation import positive_int, real_scalar


@dataclass(frozen=True)
class CorruptionConfig:
    """Declared policy for sampling self-supervised corruption masks."""
    mode: str = "random"  # 'random' | 'channel' | 'span' | 'mixed'
    rate: float = 0.2
    span_length: int = 12
    seed: Optional[int] = None

    def __post_init__(self) -> None:
        if self.mode not in {"random", "channel", "span", "mixed"}:
            raise ValueError(f"Invalid corruption mode '{self.mode}'. Expected 'random', 'channel', 'span', or 'mixed'.")
        if not 0.0 < real_scalar(self.rate) < 1.0:
            raise ValueError("Corruption rate must be in (0, 1).")
        positive_int(self.span_length)


@dataclass(frozen=True)
class ObservationSummary:
    """Audit summary of observations and withheld target counts."""
    total_observations: int
    total_masked: int
    channel_observations: tuple[int, ...]
    channel_masked: tuple[int, ...]
    mask_coverage_ratio: float


def audit_observation_coverage(
    observed: torch.Tensor,
    hidden: torch.Tensor,
) -> ObservationSummary:
    """Compute per-channel observation and masked-target counts for input lineage auditing."""
    if observed.shape != hidden.shape or observed.dtype != torch.bool or hidden.dtype != torch.bool:
        raise ValueError("Observed and hidden masks must be boolean and aligned.")
    if (hidden & ~observed).any():
        raise ValueError("Hidden mask contains unobserved positions.")

    channels = observed.shape[-1]
    obs_flat = observed.view(-1, channels)
    hid_flat = hidden.view(-1, channels)

    ch_obs = tuple(int(obs_flat[:, c].sum().item()) for c in range(channels))
    ch_hid = tuple(int(hid_flat[:, c].sum().item()) for c in range(channels))
    tot_obs = sum(ch_obs)
    tot_hid = sum(ch_hid)
    ratio = float(tot_hid / max(1, tot_obs))

    return ObservationSummary(
        total_observations=tot_obs,
        total_masked=tot_hid,
        channel_observations=ch_obs,
        channel_masked=ch_hid,
        mask_coverage_ratio=ratio,
    )


def sample_corruption_mask(
    observed: torch.Tensor,
    config: Optional[CorruptionConfig] = None,
    *,
    mode: str = "random",
    rate: float = 0.2,
    span_length: int = 12,
    generator: Optional[torch.Generator] = None,
    seed: Optional[int] = None,
) -> torch.Tensor:
    """Sample a corruption mask M strictly within observed targets O (M subset of O).

    Guarantees:
    1. M is a strict subset of O: (hidden & ~observed).any() == False.
    2. M is non-empty where observed is non-empty: (hidden & observed).any() == True.
    """
    if observed.dtype != torch.bool:
        raise ValueError("Observed mask must be boolean.")
    if not observed.any():
        raise ValueError("Observed mask has no available observations to corrupt.")

    if config is not None:
        mode = config.mode
        rate = config.rate
        span_length = config.span_length
        if config.seed is not None and generator is None and seed is None:
            seed = config.seed

    if seed is not None and generator is None:
        generator = torch.Generator(device=observed.device).manual_seed(seed)

    if not 0.0 < rate < 1.0:
        raise ValueError("Corruption rate must be in (0, 1).")
    if span_length < 1:
        raise ValueError("span_length must be >= 1.")

    orig_dim = observed.ndim
    if orig_dim == 2:
        obs_batch = observed.unsqueeze(0)
    elif orig_dim == 3:
        obs_batch = observed
    else:
        raise ValueError(f"Expected 2D (T, C) or 3D (B, T, C) tensor, got ndim={orig_dim}")

    B, T, C = obs_batch.shape
    hidden = torch.zeros_like(obs_batch, dtype=torch.bool)

    for b in range(B):
        b_obs = obs_batch[b]
        if not b_obs.any():
            continue

        selected_mode = mode
        if mode == "mixed":
            modes = ["random", "channel", "span"]
            rand_idx = int(torch.randint(0, len(modes), (1,), generator=generator, device=observed.device).item())
            selected_mode = modes[rand_idx]

        if selected_mode == "random":
            rand_vals = torch.rand(b_obs.shape, generator=generator, device=observed.device)
            m = (rand_vals < rate) & b_obs
            if not m.any():
                obs_indices = torch.nonzero(b_obs, as_tuple=False)
                pick = int(torch.randint(0, len(obs_indices), (1,), generator=generator, device=observed.device).item())
                m[obs_indices[pick, 0], obs_indices[pick, 1]] = True
            hidden[b] = m

        elif selected_mode == "channel":
            ch_with_obs = [c for c in range(C) if b_obs[:, c].any()]
            if not ch_with_obs:
                obs_indices = torch.nonzero(b_obs, as_tuple=False)
                pick = int(torch.randint(0, len(obs_indices), (1,), generator=generator, device=observed.device).item())
                hidden[b, obs_indices[pick, 0], obs_indices[pick, 1]] = True
            else:
                pick_ch_idx = int(torch.randint(0, len(ch_with_obs), (1,), generator=generator, device=observed.device).item())
                chosen_ch = ch_with_obs[pick_ch_idx]
                hidden[b, :, chosen_ch] = b_obs[:, chosen_ch]

        elif selected_mode == "span":
            eff_len = min(span_length, T)
            max_start = max(1, T - eff_len + 1)
            start_t = int(torch.randint(0, max_start, (1,), generator=generator, device=observed.device).item())
            end_t = min(T, start_t + eff_len)
            m_span = torch.zeros_like(b_obs, dtype=torch.bool)
            m_span[start_t:end_t, :] = b_obs[start_t:end_t, :]
            if not m_span.any():
                obs_indices = torch.nonzero(b_obs, as_tuple=False)
                pick = int(torch.randint(0, len(obs_indices), (1,), generator=generator, device=observed.device).item())
                m_span[obs_indices[pick, 0], obs_indices[pick, 1]] = True
            hidden[b] = m_span
        else:
            raise ValueError(f"Unknown corruption mode '{selected_mode}'")

    if not (hidden & obs_batch).any():
        obs_indices = torch.nonzero(obs_batch, as_tuple=False)
        pick = int(torch.randint(0, len(obs_indices), (1,), generator=generator, device=observed.device).item())
        hidden[obs_indices[pick, 0], obs_indices[pick, 1], obs_indices[pick, 2]] = True

    if orig_dim == 2:
        hidden = hidden.squeeze(0)

    if (hidden & ~observed).any():
        raise RuntimeError("Corruption mask invariant violated: masked unobserved entries.")
    if not (hidden & observed).any():
        raise RuntimeError("Corruption mask invariant violated: no observed targets masked.")

    return hidden


@torch.no_grad()
def compute_score_a(
    model: MaskedHydroModel,
    values: torch.Tensor,
    observed: torch.Tensor,
    *,
    aggregation: str = "mean",
    allow_missing_steps: bool = False,
) -> torch.Tensor:
    """Compute Score A: leave-channel-out cross-reconstruction anomaly score.

    Hides each physical channel across the observation sequence, evaluating
    reconstruction error strictly on observed targets.

    Args:
        model: MaskedHydroModel in eval mode.
        values: Tensor of normalized observations, shape (B, T, C) or (T, C).
        observed: Boolean observation mask, shape matching values.
        aggregation: 'mean' (temporal average over valid steps), 'tail' (issue time),
                     'max' (peak over valid steps), or 'none' (per-timestep tensor).
        allow_missing_steps: If False, enforces that every time step has at least one observation.
                             If True, computes leave-channel-out error on all observed entries and
                             skips entirely missing time steps during aggregation.

    Returns:
        Tensor of reconstruction anomaly scores.
    """
    if model.training:
        raise ValueError("Scoring requires eval mode.")
    if aggregation not in {"mean", "tail", "max", "none"}:
        raise ValueError(f"Invalid aggregation '{aggregation}'. Expected 'mean', 'tail', 'max', or 'none'.")

    orig_dim = values.ndim
    if orig_dim == 2:
        val_b = values.unsqueeze(0)
        obs_b = observed.unsqueeze(0)
    elif orig_dim == 3:
        val_b = values
        obs_b = observed
    else:
        raise ValueError(f"Expected 2D or 3D tensor, got ndim={orig_dim}")

    if not allow_missing_steps:
        scores = leave_channel_out_score(model, val_b, obs_b)
        valid_steps = obs_b.any(dim=-1)
    else:
        if obs_b.shape != val_b.shape or obs_b.dtype != torch.bool:
            raise ValueError("Observed mask must align with values.")
        if not obs_b.any():
            raise ValueError("No observed scoring targets in the input.")
        errors = torch.zeros_like(val_b)
        for channel in range(model.physical_channels):
            visible = obs_b.clone()
            visible[..., channel] = False
            _, reconstruction = model(val_b, visible)
            errors[..., channel] = (reconstruction[..., channel] - val_b[..., channel]).square()
        obs_count = obs_b.sum(dim=-1).clamp(min=1)
        scores = torch.where(obs_b, errors, torch.zeros_like(errors)).sum(dim=-1) / obs_count
        valid_steps = obs_b.any(dim=-1)

    if aggregation == "none":
        return scores.squeeze(0) if orig_dim == 2 else scores
    elif aggregation == "tail":
        res = scores[..., -1]
        return res.squeeze(0) if orig_dim == 2 else res
    elif aggregation == "max":
        masked_scores = torch.where(valid_steps, scores, torch.tensor(float('-inf'), device=scores.device))
        res = masked_scores.max(dim=-1)[0]
        return res.squeeze(0) if orig_dim == 2 else res
    elif aggregation == "mean":
        valid_float = valid_steps.float()
        counts = valid_float.sum(dim=-1).clamp(min=1.0)
        res = (scores * valid_float).sum(dim=-1) / counts
        return res.squeeze(0) if orig_dim == 2 else res


@torch.no_grad()
def compute_score_b(
    model: MaskedHydroModel,
    values: torch.Tensor,
    observed: torch.Tensor,
    latent_reference: LatentReference,
    *,
    time_idx: int = -1,
) -> np.ndarray:
    """Compute Score B: squared Mahalanobis distance from fitted latent reference.

    Evaluates causal latent state z at time_idx against the training reference distribution.

    Args:
        model: MaskedHydroModel in eval mode.
        values: Tensor of normalized observations, shape (B, T, C) or (T, C).
        observed: Boolean observation mask matching values.
        latent_reference: Fitted LatentReference.
        time_idx: Time step index for evaluation (default -1 for issue time).

    Returns:
        NumPy array of squared Mahalanobis distances (shape (B,) or scalar float).
    """
    if model.training:
        raise ValueError("Scoring requires eval mode.")
    if not isinstance(latent_reference, LatentReference):
        raise TypeError(f"Expected LatentReference, got {type(latent_reference).__name__}")

    orig_dim = values.ndim
    if orig_dim == 2:
        val_b = values.unsqueeze(0)
        obs_b = observed.unsqueeze(0)
    elif orig_dim == 3:
        val_b = values
        obs_b = observed
    else:
        raise ValueError(f"Expected 2D or 3D tensor, got ndim={orig_dim}")

    z, _ = model(val_b, obs_b)
    z_step = z[:, time_idx, :].detach().cpu().numpy().astype(np.float64)
    distances = latent_reference.squared_distance(z_step)

    if orig_dim == 2:
        return float(distances[0])
    return distances


@torch.no_grad()
def fit_latent_reference(
    model: MaskedHydroModel,
    dataloader_or_batches: Any,
    *,
    split: str = "train",
    shrinkage: float = 0.1,
    time_idx: int = -1,
) -> LatentReference:
    """Extract causal embeddings from training batches and fit an immutable LatentReference.

    Fails closed with ValueError if split != 'train' (or 'calibration').
    """
    if split not in {"train", "calibration"}:
        raise ValueError(
            f"LatentReference cannot be fitted on split '{split}'. "
            "Distribution parameters must derive strictly from 'train' or 'calibration'."
        )
    if model.training:
        raise ValueError("Latent extraction requires eval mode.")

    all_latents: list[np.ndarray] = []
    for batch in dataloader_or_batches:
        values = batch["values"]
        observed = batch["observed"]
        batch_splits = batch.get("splits")
        if batch_splits and any(s != split for s in batch_splits):
            raise ValueError(f"Batch contains samples from non-training splits: {set(batch_splits)}")

        z, _ = model(values, observed)
        z_step = z[:, time_idx, :].detach().cpu().numpy().astype(np.float64)
        all_latents.append(z_step)

    if not all_latents:
        raise ValueError("No samples available to extract latent embeddings.")

    stacked = np.concatenate(all_latents, axis=0)
    return LatentReference.fit(stacked, split=split, shrinkage=shrinkage)

