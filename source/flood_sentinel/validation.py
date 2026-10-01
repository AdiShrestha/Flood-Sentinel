"""Strict numerical inputs; parsing provider text belongs in an explicit adapter."""
from numbers import Real
import numpy as np


def real_array(values, *, allow_nan=False):
    x = np.asarray(values)
    if x.dtype.kind not in 'iuf':
        raise ValueError('Real numerical arrays required; no string, boolean, complex or object coercion.')
    x = np.asarray(x, dtype=np.float64)
    if np.isinf(x).any() or (not allow_nan and not np.isfinite(x).all()):
        raise ValueError('Nonfinite numerical input.')
    return x


def real_scalar(value):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real) or not np.isfinite(value):
        raise ValueError('A finite real scalar is required.')
    return float(value)


def positive_int(value, *, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError(f'An integer >= {minimum} is required.')
    return value


def frozen_array(values, *, integer=False):
    x = real_array(values)
    if integer:
        if np.asarray(values).dtype.kind not in 'iu':
            raise ValueError('Integer counts required.')
        x = np.asarray(values, dtype=np.int64)
    # Immutable bytes back the view, so callers cannot re-enable WRITEABLE.
    return np.frombuffer(x.tobytes(), dtype=x.dtype).reshape(x.shape)
