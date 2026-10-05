"""Deterministic physical unit conversion constants and functions.

Standardizes imperial hydrological parameters (feet, cfs) and meteorological
parameters to exact International System of Units (SI) base and derived units.
"""
from __future__ import annotations

import math
from numbers import Real

# Exact international conversion factor (1959 treaty: 1 ft = 0.3048 m)
FEET_TO_METERS: float = 0.3048
METERS_TO_FEET: float = 1.0 / FEET_TO_METERS

# Exact cubic conversion factor: 0.3048^3 m^3 / ft^3
CFS_TO_CMS: float = 0.028316846592
CMS_TO_CFS: float = 1.0 / CFS_TO_CMS

# Temperature offset from Celsius to Kelvin
CELSIUS_TO_KELVIN_OFFSET: float = 273.15


def _ensure_finite_scalar(val: Real) -> float:
    """Verify that input is a finite numeric scalar."""
    if isinstance(val, bool) or not isinstance(val, Real):
        raise ValueError(f"Value must be a numeric scalar, got {type(val).__name__}")
    f_val = float(val)
    if not math.isfinite(f_val):
        raise ValueError("Cannot convert non-finite numeric value (inf or nan)")
    return f_val


def feet_to_meters(feet: Real) -> float:
    """Convert length from feet to meters using the exact international yard/pound factor."""
    return _ensure_finite_scalar(feet) * FEET_TO_METERS


def meters_to_feet(meters: Real) -> float:
    """Convert length from meters to feet."""
    return _ensure_finite_scalar(meters) * METERS_TO_FEET


def cfs_to_cms(cfs: Real) -> float:
    """Convert volume flow from cubic feet per second (cfs) to cubic meters per second (cms)."""
    return _ensure_finite_scalar(cfs) * CFS_TO_CMS


def cms_to_cfs(cms: Real) -> float:
    """Convert volume flow from cubic meters per second (cms) to cubic feet per second (cfs)."""
    return _ensure_finite_scalar(cms) * CMS_TO_CFS


def celsius_to_kelvin(celsius: Real) -> float:
    """Convert temperature from degrees Celsius to Kelvin."""
    return _ensure_finite_scalar(celsius) + CELSIUS_TO_KELVIN_OFFSET


def kelvin_to_celsius(kelvin: Real) -> float:
    """Convert temperature from Kelvin to degrees Celsius."""
    k = _ensure_finite_scalar(kelvin)
    if k < 0.0:
        raise ValueError("Temperature in Kelvin cannot be negative (below absolute zero)")
    return k - CELSIUS_TO_KELVIN_OFFSET


_CONVERTERS = {
    ("ft", "m"): feet_to_meters,
    ("feet", "m"): feet_to_meters,
    ("m", "ft"): meters_to_feet,
    ("cfs", "m3/s"): cfs_to_cms,
    ("cfs", "cms"): cfs_to_cms,
    ("ft3/s", "m3/s"): cfs_to_cms,
    ("m3/s", "cfs"): cms_to_cfs,
    ("cms", "cfs"): cms_to_cfs,
    ("degC", "K"): celsius_to_kelvin,
    ("deg c", "K"): celsius_to_kelvin,
    ("C", "K"): celsius_to_kelvin,
    ("K", "degC"): kelvin_to_celsius,
    ("K", "C"): kelvin_to_celsius,
}


def convert_units(value: Real, from_unit: str, to_unit: str) -> float:
    """Convert value between supported physical units."""
    clean_from = from_unit.strip()
    clean_to = to_unit.strip()
    if clean_from == clean_to:
        return _ensure_finite_scalar(value)

    pair = (clean_from, clean_to)
    if pair in _CONVERTERS:
        return _CONVERTERS[pair](value)

    raise ValueError(f"Unsupported unit conversion pair: '{from_unit}' -> '{to_unit}'")
