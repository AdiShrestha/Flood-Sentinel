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
