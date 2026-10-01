"""Causal baseline operators with honest names and no generated observations."""
import numpy as np
from .validation import real_array, real_scalar


def rate_of_change(values, *, step_duration: float = 1.):
    """Change per declared step duration; timestamps/contiguity require adapter verification."""
    x = real_array(values)
    step_duration = real_scalar(step_duration)
    if step_duration <= 0: raise ValueError('Positive step duration required.')
    if x.ndim != 1 or len(x) < 2 or not np.isfinite(x).all():
        raise ValueError('Ordered, contiguous finite observations required; gaps need an explicit policy.')
    with np.errstate(over='ignore', invalid='ignore'):
        result = np.diff(x)/step_duration
    if not np.isfinite(result).all(): raise ValueError('Rate-of-change overflow.')
    return result


def persistence_forecast(latest_value, horizon_steps: int):
    latest_value = real_scalar(latest_value)
    if not np.isfinite(latest_value) or type(horizon_steps) is not int or horizon_steps < 1:
        raise ValueError('Finite last observation and positive forecast horizon required.')
    return np.full(horizon_steps, latest_value, dtype=float)


def ewma_cusum(values, *, calibration_mean: float, calibration_scale: float,
               alpha: float, slack: float, initial_ewma: float, initial_cusum: float):
    """One-sided CUSUM of EWMA-smoothed deviations, not canonical raw-observation CUSUM.

    States continue across calls; resetting per overlapping window changes the operator.
    The caller must fit parameters on permitted data and declare the sampling cadence.
    """
    x = real_array(values)
    scalars = [calibration_mean, calibration_scale, alpha, slack, initial_ewma, initial_cusum]
    calibration_mean, calibration_scale, alpha, slack, initial_ewma, initial_cusum = map(real_scalar, scalars)
    if x.ndim != 1 or not len(x) or not np.isfinite(x).all() or not np.isfinite(scalars).all():
        raise ValueError('Finite stream and fitted state parameters required.')
    if calibration_scale <= 0 or not 0 < alpha <= 1 or slack < 0 or initial_cusum < 0:
        raise ValueError('Invalid scale, EWMA coefficient, slack or initial state.')
    ewma, cusum = initial_ewma, initial_cusum; scores = []
    for value in x:
        with np.errstate(over='ignore',invalid='ignore'):
            ewma = alpha*value+(1-alpha)*ewma
            increment = (ewma-calibration_mean)/calibration_scale-slack
            candidate = cusum+increment
        if not np.isfinite([ewma, increment, candidate]).all(): raise ValueError('EWMA/CUSUM arithmetic overflow.')
        cusum = max(0., candidate)
        scores.append(cusum)
    return np.asarray(scores), {'ewma': float(ewma), 'cusum': float(cusum)}
