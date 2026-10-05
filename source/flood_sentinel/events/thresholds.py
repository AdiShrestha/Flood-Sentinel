"""Official flood category threshold definitions and configuration registry."""
from __future__ import annotations

import csv
from dataclasses import dataclass
import math
from pathlib import Path
from typing import Sequence

from flood_sentinel.acquisition.units import feet_to_meters, meters_to_feet


OFFICIAL_CATEGORIES = ("action", "minor", "moderate", "major")
CATEGORY_ORDER = {
    "action": 1,
    "minor": 2,
    "moderate": 3,
    "major": 4,
}


@dataclass(frozen=True)
class FloodThreshold:
    """Official flood category or statistical high-flow threshold."""
    site_no: str
    parameter: str
    category: str
    value_si: float
    value_raw: float
    unit_si: str
    unit_raw: str
    vertical_datum: str = "NAVD88"
    threshold_type: str = "official_nwps"

    def __post_init__(self):
        if not self.site_no or not isinstance(self.site_no, str):
            raise ValueError("site_no must be a non-empty string")
        if not self.category or not isinstance(self.category, str):
            raise ValueError("category must be a non-empty string")
        if not isinstance(self.value_si, (int, float)) or not math.isfinite(self.value_si) or self.value_si <= 0.0:
            raise ValueError(f"value_si must be a positive finite float, got {self.value_si}")
        if not isinstance(self.value_raw, (int, float)) or not math.isfinite(self.value_raw) or self.value_raw <= 0.0:
            raise ValueError(f"value_raw must be a positive finite float, got {self.value_raw}")
        if self.threshold_type not in {"official_nwps", "training_quantile"}:
            raise ValueError(f"threshold_type must be 'official_nwps' or 'training_quantile', got '{self.threshold_type}'")


class ThresholdRegistry:
    """In-memory registry of validated station flood thresholds."""

    def __init__(self, thresholds: Sequence[FloodThreshold] | None = None):
        self._by_key: dict[tuple[str, str], FloodThreshold] = {}
        if thresholds:
            for t in thresholds:
                self.register(t)

    def register(self, threshold: FloodThreshold) -> None:
        key = (threshold.site_no, threshold.category)
        self._by_key[key] = threshold

    def get(self, site_no: str, category: str) -> FloodThreshold | None:
        return self._by_key.get((site_no, category))

    def get_all_for_site(self, site_no: str) -> list[FloodThreshold]:
        matches = [t for (s, _), t in self._by_key.items() if s == site_no]
        return sorted(matches, key=lambda t: CATEGORY_ORDER.get(t.category, 99))

    def sites(self) -> list[str]:
        return sorted(list({s for s, _ in self._by_key}))

    def __len__(self) -> int:
        return len(self._by_key)

    @classmethod
    def from_source_records(cls, csv_path: Path) -> ThresholdRegistry:
        """Extract official NWPS thresholds from source_records.csv."""
        if not csv_path.is_file():
            raise FileNotFoundError(f"Source records CSV not found: {csv_path}")

        registry = cls()
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("provider") != "NOAA-NWPS":
                    continue
                param = row.get("parameter", "")
                if not param.startswith("flood_stage_"):
                    continue

                # Expected param format: flood_stage_{category}_m
                parts = param.split("_")
                if len(parts) < 4:
                    continue
                category = parts[2]
                site_no = row.get("site_no", "")
                val_si = float(row.get("value_si", 0.0))
                val_raw = round(meters_to_feet(val_si), 2)

                threshold = FloodThreshold(
                    site_no=site_no,
                    parameter="gage_height_m",
                    category=category,
                    value_si=val_si,
                    value_raw=val_raw,
                    unit_si="m",
                    unit_raw="ft",
                    vertical_datum="NAVD88",
                    threshold_type="official_nwps",
                )
                registry.register(threshold)

        return registry
