"""Flood event definition, detection state machine, and episode catalog."""

from .thresholds import (
    OFFICIAL_CATEGORIES,
    CATEGORY_ORDER,
    FloodThreshold,
    ThresholdRegistry,
)
from .detector import (
    EventEpisode,
    detect_episodes,
)
from .catalog import (
    CATALOG_COLUMNS,
    CATALOG_SCHEMA,
    episodes_to_pyarrow_table,
    write_catalog_files,
    load_catalog_parquet,
    load_catalog_csv,
)

__all__ = [
    "OFFICIAL_CATEGORIES",
    "CATEGORY_ORDER",
    "FloodThreshold",
    "ThresholdRegistry",
    "EventEpisode",
    "detect_episodes",
    "CATALOG_COLUMNS",
    "CATALOG_SCHEMA",
    "episodes_to_pyarrow_table",
    "write_catalog_files",
    "load_catalog_parquet",
    "load_catalog_csv",
]
