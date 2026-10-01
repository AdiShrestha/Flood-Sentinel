"""Raw-observation scaling; missing values are distinct from observed zero."""
from dataclasses import dataclass
import numpy as np
from .validation import real_array, frozen_array


def observations(values):
    array = real_array(values, allow_nan=True)
    if array.ndim != 2 or not array.size or np.isinf(array).any():
        raise ValueError('Expected a nonempty (observations, channels) matrix; NaN is missing, infinity invalid.')
    return array


@dataclass(frozen=True)
class Normalizer:
    mean: np.ndarray
    scale: np.ndarray
    median: np.ndarray
    count: np.ndarray

    def __post_init__(self):
        for name in ('mean', 'scale', 'median', 'count'):
            object.__setattr__(self, name, frozen_array(getattr(self, name), integer=name == 'count'))
        if self.mean.ndim != 1 or not self.mean.size or any(getattr(self, n).shape != self.mean.shape for n in ('scale','median','count')):
            raise ValueError('Aligned nonempty fitted channel vectors required.')
        if (self.scale <= 0).any() or (self.count < 2).any():
            raise ValueError('Positive scales and >=2 observations per channel required.')

    @classmethod
    def fit(cls, values, *, split: str):
        if split != 'train': raise ValueError('Fit scaling exclusively on declared raw training observations.')
        x = observations(values)
        count = np.isfinite(x).sum(axis=0)
        if (count < 2).any(): raise ValueError('A channel has fewer than two observations; acquire data or remove it explicitly.')
        scale = np.nanstd(x, axis=0, ddof=0)
        if (scale <= 0).any(): raise ValueError('Constant channels must be removed explicitly, not given a invented variance.')
        mean = np.nanmean(x, axis=0); median = np.nanmedian(x, axis=0)
        if not np.isfinite(mean).all() or not np.isfinite(scale).all() or not np.isfinite(median).all():
            raise ValueError('Scaling overflow; do not sanitize it into plausible statistics.')
        return cls(mean, scale, median, count)

    def transform(self, values):
        """Return normalized values and an observed mask; imputation is train-median only."""
        x = observations(values)
        if x.shape[1] != len(self.mean): raise ValueError('Channel count differs from fitted normalization.')
        mask = np.isfinite(x)
        filled = np.where(mask, x, self.median)
        scaled = (filled - self.mean) / self.scale
        if not np.isfinite(scaled).all(): raise ValueError('Normalization produced nonfinite values.')
        return scaled, mask
