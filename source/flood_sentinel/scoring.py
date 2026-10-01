"""Defined anomaly operators. They are raw scores, not calibrated probabilities."""
from dataclasses import dataclass
import numpy as np
from .validation import real_array, real_scalar, positive_int, frozen_array


def finite_matrix(values):
    x = real_array(values)
    if x.ndim != 2 or not x.size or not np.isfinite(x).all():
        raise ValueError('A nonempty finite (observations, dimensions) matrix is required.')
    return x


@dataclass(frozen=True)
class RobustCalibration:
    median: float
    iqr: float
    count: int

    def __post_init__(self):
        real_scalar(self.median)
        if real_scalar(self.iqr) <= 0: raise ValueError('Positive calibration IQR required.')
        positive_int(self.count, minimum=2)

    @classmethod
    def fit(cls, scores, *, split: str, min_observations: int):
        if split not in {'train', 'calibration'}: raise ValueError('Test/evaluation scores cannot fit calibration.')
        x = real_array(scores)
        if type(min_observations) is not int or min_observations < 2:
            raise ValueError('Preregister a minimum calibration count >=2; this floor is not a precision guarantee.')
        if x.ndim != 1 or len(x) < min_observations or not np.isfinite(x).all():
            raise ValueError('Insufficient or invalid calibration scores; no fallback scale.')
        with np.errstate(over='ignore', invalid='ignore'):
            lo, hi = np.quantile(x, [.25, .75]); width = hi-lo
            median = float(np.median(x))
        if not np.isfinite(width) or not np.isfinite(median) or width <= 0:
            raise ValueError('Calibration IQR is zero or nonfinite; do not manufacture a scale.')
        return cls(median, float(width), len(x))

    def transform(self, scores):
        x = real_array(scores)
        if not np.isfinite(x).all() or not np.isfinite(self.iqr) or not np.isfinite(self.median) or self.iqr <= 0:
            raise ValueError('Invalid score or calibration scale.')
        with np.errstate(over='ignore', invalid='ignore'):
            result = (x - self.median) / self.iqr
        if not np.isfinite(result).all(): raise ValueError('Calibration overflow; no finite-score substitute.')
        return result


@dataclass(frozen=True)
class LatentReference:
    mean: np.ndarray
    cholesky: np.ndarray
    shrinkage: float
    count: int

    def __post_init__(self):
        object.__setattr__(self, 'mean', frozen_array(self.mean))
        object.__setattr__(self, 'cholesky', frozen_array(self.cholesky))
        positive_int(self.count, minimum=2)
        if not 0 < real_scalar(self.shrinkage) <= 1: raise ValueError('Invalid shrinkage.')
        d = self.mean.size
        if self.mean.ndim != 1 or not d or self.cholesky.shape != (d,d):
            raise ValueError('Aligned nonempty mean and Cholesky factor required.')
        if not np.array_equal(self.cholesky, np.tril(self.cholesky)) or (np.diag(self.cholesky) <= 0).any():
            raise ValueError('Lower-triangular Cholesky factor with positive diagonal required.')

    @classmethod
    def fit(cls, embeddings, *, split: str, shrinkage: float):
        if split not in {'train', 'calibration'}: raise ValueError('Latent reference cannot fit evaluation embeddings.')
        x = finite_matrix(embeddings)
        shrinkage = real_scalar(shrinkage)
        if len(x) < 2 or not 0 < shrinkage <= 1: raise ValueError('Need >=2 baseline rows and preregistered shrinkage in (0,1].')
        d = x.shape[1]
        with np.errstate(over='ignore', invalid='ignore'):
            mu = x.mean(axis=0)
            cov = (x-mu).T @ (x-mu) / (len(x)-1)
            target = np.trace(cov) / d
        if not np.isfinite(mu).all() or not np.isfinite(cov).all() or not np.isfinite(target):
            raise ValueError('Reference covariance overflow; do not sanitize it.')
        if target <= 0: raise ValueError('Collapsed baseline embeddings cannot define a distance.')
        covariance = (1-shrinkage)*cov + shrinkage*target*np.eye(d)
        return cls(mu, np.linalg.cholesky(covariance), float(shrinkage), len(x))

    def squared_distance(self, embeddings):
        x = finite_matrix(embeddings)
        if x.shape[1] != len(self.mean): raise ValueError('Embedding dimension mismatch.')
        with np.errstate(over='ignore', invalid='ignore'):
            whitened = np.linalg.solve(self.cholesky, (x-self.mean).T)
            result = (whitened**2).sum(axis=0)
        if not np.isfinite(result).all(): raise ValueError('Distance overflow or invalid fitted reference.')
        return result


def latent_step_change(embeddings):
    """Euclidean change between adjacent valid steps; no claim of future prediction."""
    x = finite_matrix(embeddings)
    if len(x) < 2: raise ValueError('At least two adjacent embeddings are required.')
    with np.errstate(over='ignore', invalid='ignore'):
        result = np.linalg.norm(np.diff(x, axis=0), axis=1)
    if not np.isfinite(result).all(): raise ValueError('Latent change overflow.')
    return result
