"""Causal baseline operators with honest names and no generated observations."""
import numpy as np


def rate_of_change(values):
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or len(x) < 2 or not np.isfinite(x).all():
        raise ValueError('Ordered, contiguous finite observations required; gaps need an explicit policy.')
    return np.diff(x)


def persistence_forecast(latest_value, horizon_steps: int):
    if not np.isfinite(latest_value) or type(horizon_steps) is not int or horizon_steps < 1:
        raise ValueError('Finite last observation and positive forecast horizon required.')
    return np.full(horizon_steps, latest_value, dtype=float)


def ewma_cusum(values, *, calibration_mean: float, calibration_scale: float,
               alpha: float, slack: float, initial_ewma: float, initial_cusum: float):
    """Continuous state evolution; resetting per overlapping window changes the operator."""
    x = np.asarray(values, dtype=float)
    scalars = [calibration_mean, calibration_scale, alpha, slack, initial_ewma, initial_cusum]
    if x.ndim != 1 or not len(x) or not np.isfinite(x).all() or not np.isfinite(scalars).all():
        raise ValueError('Finite stream and fitted state parameters required.')
    if calibration_scale <= 0 or not 0 < alpha <= 1 or slack < 0 or initial_cusum < 0:
        raise ValueError('Invalid scale, EWMA coefficient, slack or initial state.')
    ewma, cusum = initial_ewma, initial_cusum; scores = []
    for value in x:
        ewma = alpha*value+(1-alpha)*ewma
        cusum = max(0., cusum+(ewma-calibration_mean)/calibration_scale-slack)
        scores.append(cusum)
    return np.asarray(scores), {'ewma': float(ewma), 'cusum': float(cusum)}
