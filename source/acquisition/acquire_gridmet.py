"""Meteorological Forcing Acquisition from gridMET (C-ACQ-MET / C01-04).

Acquires daily precipitation (pr), minimum temperature (tmmn), and maximum
temperature (tmmx) from the Climatology Lab gridMET OPeNDAP dataset across
1990-01-01 to 2023-12-31 for all pilot panel streamgages.
Applies information-state vintage tagging per INV-021 (pre-2013 reanalysis
vs. post-2013 near-real-time proxy).
"""

import hashlib
import json
import math
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import CHUNK01_DATA_DIR, CHUNK01_DIR, CHUNK01_MANIFESTS_DIR
from source.utils.logging_config import get_logger
from source.utils.manifest import write_acquisition_provenance, write_data_manifest

logger = get_logger("acquire_gridmet")

# gridMET grid geometry parameters
GRIDMET_LAT_ORIGIN = 49.400000000000000
GRIDMET_LON_ORIGIN = -124.7666666333333
GRIDMET_CELL_SIZE = 1.0 / 24.0  # ~0.041666666666666664 degrees (~4 km)

# gridMET THREDDS base URL
GRIDMET_THREDDS_BASE = "http://thredds.northwestknowledge.net:8080/thredds/dodsC"

# Day 0 in gridMET aggregations is 1979-01-01
GRIDMET_ORIGIN_DATE = datetime(1979, 1, 1)


def compute_lat_lon_grid_indices(lat: float, lon: float) -> Tuple[int, int]:
    """Calculate gridMET matrix indices (lat_idx, lon_idx) from geographic coordinates."""
    lat_idx = int(round((GRIDMET_LAT_ORIGIN - lat) / GRIDMET_CELL_SIZE))
    lon_idx = int(round((lon - GRIDMET_LON_ORIGIN) / GRIDMET_CELL_SIZE))
    return lat_idx, lon_idx


def compute_day_indices(start_date: str, end_date: str) -> Tuple[int, int]:
    """Calculate gridMET day indices for a date range."""
    dt_start = datetime.strptime(start_date, "%Y-%m-%d")
    dt_end = datetime.strptime(end_date, "%Y-%m-%d")
    idx_start = (dt_start - GRIDMET_ORIGIN_DATE).days
    idx_end = (dt_end - GRIDMET_ORIGIN_DATE).days
    return idx_start, idx_end


def compute_shannon_entropy(values: np.ndarray, num_bins: int = 50) -> float:
    """Compute Shannon entropy (in nats) of a continuous 1D numeric array."""
    valid = values[~np.isnan(values)]
    if len(valid) < 2:
        return 0.0
    hist, _ = np.histogram(valid, bins=num_bins, density=True)
    hist = hist[hist > 0]
    bin_width = (np.max(valid) - np.min(valid)) / num_bins
    if bin_width <= 0:
        return 0.0
    p = hist * bin_width
    p = p[p > 0]
    return float(-np.sum(p * np.log(p)))


def pull_gridmet_variable_slice(
    var_short: str,
    var_array_name: str,
    day_start: int,
    day_end: int,
    lat_idx: int,
    lon_idx: int,
    max_retries: int = 3,
) -> Tuple[Optional[List[float]], Dict[str, Any]]:
    """Pull time-series slice for a variable and grid cell via OPeNDAP ASCII endpoint."""
    url = (
        f"{GRIDMET_THREDDS_BASE}/agg_met_{var_short}_1979_CurrentYear_CONUS.nc.ascii?"
        f"{var_array_name}[{day_start}:{day_end}][{lat_idx}][{lon_idx}]"
    )

    meta: Dict[str, Any] = {
        "url": url,
        "variable": var_short,
        "day_slice": [day_start, day_end],
        "grid_cell": [lat_idx, lon_idx],
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "http_status": None,
        "response_sha256": None,
        "error": None
    }

    resp = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, timeout=45)
            meta["http_status"] = resp.status_code
            if resp.status_code == 200:
                break
            time.sleep(2 * attempt)
        except Exception as e:
            meta["error"] = str(e)
            time.sleep(2 * attempt)

    if resp is None or resp.status_code != 200:
        logger.error(f"Failed to fetch {var_short} at ({lat_idx}, {lon_idx}), status {meta['http_status']}")
        return None, meta

    raw_text = resp.text
    meta["response_sha256"] = f"sha256:{hashlib.sha256(resp.content).hexdigest()}"

    data_section = raw_text.split("---------------------------------------------")[-1]
    header_pattern = rf"{var_array_name}\.{var_array_name}\[\d+\]\[\d+\]\[\d+\]\s*\n(.*?)(?:\n\s*\n|\Z)"
    match = re.search(header_pattern, data_section, re.DOTALL)
    if not match:
        meta["error"] = "Could not parse array section from DODS ASCII output"
        return None, meta

    lines = match.group(1).strip().splitlines()
    raw_vals = [float(l.split(",")[-1].strip()) for l in lines if "," in l]
    return raw_vals, meta


def fetch_site_coordinates(site_numbers: List[str]) -> Dict[str, Tuple[float, float]]:
    """Fetch official latitude and longitude for USGS station IDs from NWIS."""
    url = f"https://waterservices.usgs.gov/nwis/site/?format=rdb&sites={','.join(site_numbers)}"
    resp = requests.get(url, timeout=20)
    coords: Dict[str, Tuple[float, float]] = {}
    for line in resp.text.splitlines():
        if not line.startswith("#") and line.strip():
            parts = line.split("\t")
            if len(parts) > 5 and parts[1] in site_numbers:
                coords[parts[1]] = (float(parts[4]), float(parts[5]))
    return coords


def acquire_site_meteorology(
    site_no: str,
    lat: float,
    lon: float,
    start_date: str = "1990-01-01",
    end_date: str = "2023-12-31",
) -> Tuple[Optional[pd.DataFrame], List[Dict[str, Any]]]:
    """Pull and calibrate precipitation, tmin, and tmax for a single USGS gauge."""
    lat_idx, lon_idx = compute_lat_lon_grid_indices(lat, lon)
    day_start, day_end = compute_day_indices(start_date, end_date)

    provenance_calls = []

    # 1. Pull precipitation (pr)
    pr_raw, pr_meta = pull_gridmet_variable_slice(
        "pr", "precipitation_amount", day_start, day_end, lat_idx, lon_idx
    )
    provenance_calls.append(pr_meta)
    if pr_raw is None:
        return None, provenance_calls

    # 2. Pull tmin (tmmn)
    tmmn_raw, tmmn_meta = pull_gridmet_variable_slice(
        "tmmn", "daily_minimum_temperature", day_start, day_end, lat_idx, lon_idx
    )
    provenance_calls.append(tmmn_meta)
    if tmmn_raw is None:
        return None, provenance_calls

    # 3. Pull tmax (tmmx)
    tmmx_raw, tmmx_meta = pull_gridmet_variable_slice(
        "tmmx", "daily_maximum_temperature", day_start, day_end, lat_idx, lon_idx
    )
    provenance_calls.append(tmmx_meta)
    if tmmx_raw is None:
        return None, provenance_calls

    # Physical unit conversions:
    # pr: scale_factor 0.1, units mm
    # tmmn: scale_factor 0.1, add_offset 210.0 (Kelvin) -> Celsius = raw * 0.1 - 63.15
    # tmmx: scale_factor 0.1, add_offset 220.0 (Kelvin) -> Celsius = raw * 0.1 - 53.15
    pr_mm = [round(v * 0.1, 2) if v < 32000 else np.nan for v in pr_raw]
    tmin_c = [round(v * 0.1 - 63.15, 2) if v < 32000 else np.nan for v in tmmn_raw]
    tmax_c = [round(v * 0.1 - 53.15, 2) if v < 32000 else np.nan for v in tmmx_raw]

    dates = pd.date_range(start=start_date, end=end_date, freq="D").strftime("%Y-%m-%d")
    vintages = [
        "nrt_proxy_available" if d >= "2013-01-01" else "pre_nrt_reanalysis_only"
        for d in dates
    ]

    df = pd.DataFrame({
        "date": dates,
        "site_no": site_no,
        "precipitation_mm": pr_mm,
        "tmin_c": tmin_c,
        "tmax_c": tmax_c,
        "vintage_id": vintages
    })

    return df, provenance_calls


def execute_gridmet_acquisition() -> None:
    """Execute gridMET meteorological acquisition across all pilot streamgages."""
    pilot_panel_path = CHUNK01_DIR / "pilot_panel.json"
    with open(pilot_panel_path, "r", encoding="utf-8") as f:
        panel_data = json.load(f)

    gauges = panel_data.get("gauges", [])
    site_numbers = [g["site_no"] for g in gauges]

    logger.info("Resolving gauge station coordinates from USGS NWIS...")
    site_coords = fetch_site_coordinates(site_numbers)

    gridmet_out_dir = CHUNK01_DATA_DIR / "gridmet"
    gridmet_out_dir.mkdir(parents=True, exist_ok=True)

    all_dfs: List[pd.DataFrame] = []
    all_provenance_calls: List[Dict[str, Any]] = []
    downloaded_files: List[Dict[str, Any]] = []

    logger.info(f"Starting gridMET acquisition for {len(gauges)} pilot streamgages...")

    for idx, g in enumerate(gauges, 1):
        site_no = g["site_no"]
        coords = site_coords.get(site_no)
        if not coords:
            raise RuntimeError(f"Could not resolve coordinates for gauge {site_no}")

        lat, lon = coords
        logger.info(f"[{idx}/{len(gauges)}] Fetching gridMET forcing for {site_no} at ({lat:.4f}, {lon:.4f})...")

        df, calls = acquire_site_meteorology(site_no, lat, lon)
        all_provenance_calls.extend(calls)

        if df is None:
            raise RuntimeError(f"Failed to acquire gridMET data for gauge {site_no}")

        # Save to Parquet per site
        site_dir = gridmet_out_dir / site_no
        site_dir.mkdir(parents=True, exist_ok=True)
        parquet_file = site_dir / "gridmet_daily.parquet"
        df.to_parquet(parquet_file, index=False)

        file_bytes = parquet_file.read_bytes()
        downloaded_files.append({
            "filename": f"gridmet/{site_no}/gridmet_daily.parquet",
            "size_bytes": len(file_bytes),
            "checksum": f"sha256:{hashlib.sha256(file_bytes).hexdigest()}"
        })

        all_dfs.append(df)
        time.sleep(0.3)

    logger.info(f"Successfully acquired gridMET meteorological data for all {len(gauges)} gauges.")

    # Aggregate stats for data_manifest
    combined = pd.concat(all_dfs, ignore_index=True)
    total_expected = len(gauges) * len(pd.date_range("1990-01-01", "2023-12-31", freq="D"))
    total_valid_pr = combined["precipitation_mm"].notna().sum()
    gap_rate_pct = float(round((1.0 - (total_valid_pr / total_expected)) * 100.0, 4))

    pr_vals = combined["precipitation_mm"].dropna().values
    tmin_vals = combined["tmin_c"].dropna().values
    tmax_vals = combined["tmax_c"].dropna().values

    dist_stats = {
        "precipitation_mm": {
            "variance": float(np.var(pr_vals)),
            "entropy": float(compute_shannon_entropy(pr_vals))
        },
        "tmin_c": {
            "variance": float(np.var(tmin_vals)),
            "entropy": float(compute_shannon_entropy(tmin_vals))
        },
        "tmax_c": {
            "variance": float(np.var(tmax_vals)),
            "entropy": float(compute_shannon_entropy(tmax_vals))
        }
    }

    data_manifest = {
        "gap_rate_pct": gap_rate_pct,
        "distribution_stats": dist_stats,
        "temporal_range": {
            "start": "1990-01-01",
            "end": "2023-12-31"
        },
        "sensors_present": [
            "gridMET_pr_precipitation",
            "gridMET_tmmn_minimum_temperature",
            "gridMET_tmmx_maximum_temperature"
        ],
        "channel_schema": {
            "column_order": [
                "date",
                "site_no",
                "precipitation_mm",
                "tmin_c",
                "tmax_c",
                "vintage_id"
            ],
            "units": {
                "date": "YYYY-MM-DD",
                "site_no": "USGS station identifier",
                "precipitation_mm": "mm/day",
                "tmin_c": "degrees Celsius",
                "tmax_c": "degrees Celsius",
                "vintage_id": "information-state vintage identifier"
            },
            "physical_range": {
                "precipitation_mm": {
                    "min": float(np.min(pr_vals)),
                    "max": float(np.max(pr_vals))
                },
                "tmin_c": {
                    "min": float(np.min(tmin_vals)),
                    "max": float(np.max(tmin_vals))
                },
                "tmax_c": {
                    "min": float(np.min(tmax_vals)),
                    "max": float(np.max(tmax_vals))
                }
            }
        },
        "provenance_chain": {
            "precipitation_mm": {
                "raw_product": "gridMET daily precipitation (pr) from University of Idaho Climatology Lab OPeNDAP",
                "transformation_steps": [
                    "HTTP OPeNDAP query to thredds.northwestknowledge.net:8080/thredds/dodsC/agg_met_pr_1979_CurrentYear_CONUS.nc",
                    "Nearest-neighbor spatial extraction for USGS station coordinates",
                    "Convert raw UInt16 to float64 via scale factor 0.1",
                    "Serialize to columnar Parquet"
                ],
                "undocumented_step": False
            },
            "tmin_c": {
                "raw_product": "gridMET daily minimum temperature (tmmn) from University of Idaho Climatology Lab OPeNDAP",
                "transformation_steps": [
                    "HTTP OPeNDAP query to thredds.northwestknowledge.net:8080/thredds/dodsC/agg_met_tmmn_1979_CurrentYear_CONUS.nc",
                    "Nearest-neighbor spatial extraction for USGS station coordinates",
                    "Convert raw UInt16 to Kelvin (raw * 0.1 + 210.0) then to Celsius (K - 273.15)",
                    "Serialize to columnar Parquet"
                ],
                "undocumented_step": False
            },
            "tmax_c": {
                "raw_product": "gridMET daily maximum temperature (tmmx) from University of Idaho Climatology Lab OPeNDAP",
                "transformation_steps": [
                    "HTTP OPeNDAP query to thredds.northwestknowledge.net:8080/thredds/dodsC/agg_met_tmmx_1979_CurrentYear_CONUS.nc",
                    "Nearest-neighbor spatial extraction for USGS station coordinates",
                    "Convert raw UInt16 to Kelvin (raw * 0.1 + 220.0) then to Celsius (K - 273.15)",
                    "Serialize to columnar Parquet"
                ],
                "undocumented_step": False
            }
        }
    }

    manifest_path = CHUNK01_MANIFESTS_DIR / "gridmet_data_manifest.json"
    write_data_manifest(manifest_path, data_manifest)
    logger.info(f"gridMET data manifest written to {manifest_path}")

    provenance_manifest = {
        "source": "University of Idaho Climatology Lab (gridMET)",
        "api_endpoint": GRIDMET_THREDDS_BASE,
        "authentication_method": "None (public OPeNDAP / THREDDS)",
        "query_parameters": {
            "variables": ["pr", "tmmn", "tmmx"],
            "date_range": ["1990-01-01", "2023-12-31"],
            "spatial_resolution": "1/24 degree (~4km)"
        },
        "total_api_calls": len(all_provenance_calls),
        "total_scenes_returned": len(gauges),
        "first_scene_date": "1990-01-01T00:00:00Z",
        "last_scene_date": "2023-12-31T00:00:00Z",
        "http_status_codes": list({c["http_status"] for c in all_provenance_calls if c["http_status"] is not None}),
        "response_payload_hash": all_provenance_calls[0]["response_sha256"] if all_provenance_calls else "sha256:none",
        "downloaded_file_manifest": downloaded_files,
        "execution_environment": {
            "network_reachable": True,
            "sandbox_bypass": True
        }
    }

    provenance_path = CHUNK01_MANIFESTS_DIR / "gridmet_acquisition_provenance.json"
    write_acquisition_provenance(provenance_path, provenance_manifest)
    logger.info(f"gridMET acquisition provenance written to {provenance_path}")


def main() -> None:
    execute_gridmet_acquisition()


if __name__ == "__main__":
    main()
