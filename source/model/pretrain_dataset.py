"""HydroPretrainDataset: Self-Supervised Masked Temporal Reconstruction Dataset (C04-04 / FR-009 / INV-001).

Implements PyTorch Dataset for C-ENCODER pretraining:
1. Slices 365-day sequences of 6 continuous physical channels from Chunk 02 daily observations.
2. Applies train-split normalization statistics (L1.2 closure).
3. Generates dynamic random binary temporal masks (masking rate r=0.15).
4. Strictly isolated from flood event labels or target exceedances (INV-001).
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import (
    CHUNK02_DATA_DIR,
    CHUNK03_DATA_DIR,
    CHUNK03_DIR,
)
from source.utils.logging_config import get_logger

logger = get_logger("pretrain_dataset")

# 6 Primary Physical Input Channels
PHYSICAL_CHANNELS = [
    "discharge_cfs",
    "gage_height_ft",
    "precipitation_mm",
    "temperature_min_degc",
    "temperature_max_degc",
    "swe_mm"
]


class HydroPretrainDataset(Dataset):
    """PyTorch Dataset yielding masked 365-day multi-channel hydrological sequences."""

    def __init__(
        self,
        feature_matrix_path: Optional[Path] = None,
        norm_params_path: Optional[Path] = None,
        mask_rate: float = 0.15,
        max_samples: Optional[int] = None,
        precache: bool = True
    ) -> None:
        super().__init__()
        self.mask_rate = mask_rate

        if feature_matrix_path is None:
            feature_matrix_path = CHUNK03_DATA_DIR / "feature_matrix_train.parquet"
        if norm_params_path is None:
            norm_params_path = CHUNK03_DIR / "normalization_params.json"

        # Load window metadata
        self.df_windows = pd.read_parquet(feature_matrix_path)
        if max_samples is not None:
            self.df_windows = self.df_windows.iloc[:max_samples].reset_index(drop=True)

        # Load train-split normalization params
        with open(norm_params_path, "r", encoding="utf-8") as f:
            self.norm_params = json.load(f)

        self.channel_stats = {
            "discharge_cfs": (
                self.norm_params["channels"]["discharge_cfs_mean"]["mean"],
                self.norm_params["channels"]["discharge_cfs_mean"]["std"]
            ),
            "gage_height_ft": (
                self.norm_params["channels"]["gage_height_ft_mean"]["mean"],
                self.norm_params["channels"]["gage_height_ft_mean"]["std"]
            ),
            "precipitation_mm": (
                self.norm_params["channels"]["gridmet_pr_mm_mean"]["mean"],
                self.norm_params["channels"]["gridmet_pr_mm_mean"]["std"]
            ),
            "temperature_min_degc": (
                self.norm_params["channels"]["gridmet_tmmn_degc_mean"]["mean"],
                self.norm_params["channels"]["gridmet_tmmn_degc_mean"]["std"]
            ),
            "temperature_max_degc": (
                self.norm_params["channels"]["gridmet_tmmx_degc_mean"]["mean"],
                self.norm_params["channels"]["gridmet_tmmx_degc_mean"]["std"]
            ),
            "swe_mm": (
                self.norm_params["channels"]["snodas_swe_mm_mean"]["mean"],
                self.norm_params["channels"]["snodas_swe_mm_mean"]["std"]
            )
        }

        # Cache daily observational data per gauge
        self.gauge_daily_cache: Dict[str, pd.DataFrame] = {}
        if precache:
            self._load_daily_cache()

    def _load_daily_cache(self) -> None:
        """Load and merge daily continuous physical channels per gauge."""
        unique_gauges = self.df_windows["gauge_id"].unique()
        logger.info(f"Loading daily observational cache for {len(unique_gauges)} training gauges...")

        for gauge_id in unique_gauges:
            # 1. USGS
            usgs_file = CHUNK02_DATA_DIR / "usgs" / gauge_id / "daily_streamflow.parquet"
            if usgs_file.exists():
                df_usgs = pd.read_parquet(usgs_file)[["datetime", "discharge_cfs", "gage_height_ft"]].copy()
                df_usgs["datetime"] = pd.to_datetime(df_usgs["datetime"]).dt.tz_localize(None)
            else:
                df_usgs = pd.DataFrame(columns=["datetime", "discharge_cfs", "gage_height_ft"])

            # 2. gridMET
            gridmet_file = CHUNK02_DATA_DIR / "gridmet" / gauge_id / "gridmet_daily.parquet"
            if gridmet_file.exists():
                df_gridmet = pd.read_parquet(gridmet_file)[["date", "precipitation_mm", "tmin_c", "tmax_c"]].copy()
                df_gridmet.rename(columns={"date": "datetime", "tmin_c": "temperature_min_degc", "tmax_c": "temperature_max_degc"}, inplace=True)
                df_gridmet["datetime"] = pd.to_datetime(df_gridmet["datetime"]).dt.tz_localize(None)
            else:
                df_gridmet = pd.DataFrame(columns=["datetime", "precipitation_mm", "temperature_min_degc", "temperature_max_degc"])

            # 3. SNODAS
            snodas_file = CHUNK02_DATA_DIR / "snodas" / gauge_id / "snodas_daily.parquet"
            if snodas_file.exists():
                df_snodas = pd.read_parquet(snodas_file)[["date", "swe_mm"]].copy()
                df_snodas.rename(columns={"date": "datetime"}, inplace=True)
                df_snodas["datetime"] = pd.to_datetime(df_snodas["datetime"]).dt.tz_localize(None)
            else:
                df_snodas = pd.DataFrame(columns=["datetime", "swe_mm"])

            # Merge
            df_merged = df_usgs.merge(df_gridmet, on="datetime", how="outer").merge(df_snodas, on="datetime", how="outer")
            df_merged = df_merged.sort_values("datetime").reset_index(drop=True)
            df_merged.set_index("datetime", inplace=True)

            # Fill missing/NaN with 0.0 before normalization (e.g. non-snow basins or gage height absent)
            for col in PHYSICAL_CHANNELS:
                if col not in df_merged.columns:
                    df_merged[col] = 0.0
                else:
                    df_merged[col] = df_merged[col].fillna(0.0)

            # Normalize using train-split statistics
            for col in PHYSICAL_CHANNELS:
                mean, std = self.channel_stats[col]
                std_safe = std if std > 1e-6 else 1.0
                df_merged[col] = (df_merged[col] - mean) / std_safe

            self.gauge_daily_cache[gauge_id] = df_merged

        logger.info("Daily observational cache loaded successfully.")

    def __len__(self) -> int:
        return len(self.df_windows)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        row = self.df_windows.iloc[idx]
        gauge_id = row["gauge_id"]
        start_date = pd.to_datetime(row["start_date"]).tz_localize(None)
        end_date = pd.to_datetime(row["end_date"]).tz_localize(None)

        df_gauge = self.gauge_daily_cache.get(gauge_id)
        if df_gauge is None:
            arr = np.zeros((365, len(PHYSICAL_CHANNELS)), dtype=np.float32)
        else:
            df_slice = df_gauge.loc[start_date:end_date, PHYSICAL_CHANNELS]
            if len(df_slice) != 365:
                full_idx = pd.date_range(start_date, periods=365, freq="D")
                df_slice = df_slice.reindex(full_idx, fill_value=0.0)
            arr = df_slice.values.astype(np.float32)

        x_target = torch.from_numpy(arr)  # (365, 6)

        # Generate dynamic random binary mask: 1 = masked, 0 = unmasked
        mask = (torch.rand_like(x_target) < self.mask_rate).float()  # (365, 6)
        x_masked = x_target * (1.0 - mask)  # Masked inputs zeroed out

        return x_masked, x_target, mask


def main() -> None:
    logger.info("Testing HydroPretrainDataset...")
    dataset = HydroPretrainDataset(max_samples=10, precache=True)
    logger.info(f"Dataset length: {len(dataset)}")

    x_masked, x_target, mask = dataset[0]
    logger.info(f"x_masked shape: {x_masked.shape}")
    logger.info(f"x_target shape: {x_target.shape}")
    logger.info(f"mask shape:     {mask.shape}")
    logger.info(f"Observed Mask Rate: {mask.mean().item():.4f}")

    assert x_masked.shape == (365, 6), f"Unexpected x_masked shape: {x_masked.shape}"
    assert x_target.shape == (365, 6), f"Unexpected x_target shape: {x_target.shape}"
    assert mask.shape == (365, 6), f"Unexpected mask shape: {mask.shape}"
    logger.info("HydroPretrainDataset test PASSED.")


if __name__ == "__main__":
    main()
