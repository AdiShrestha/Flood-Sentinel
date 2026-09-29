"""Pilot Gauge Panel Selection for flood-sentinel (Chunk 01).

Selects 18 stratified USGS streamgages spanning 6 HUC hydrologic regions,
balancing reference and non-reference (regulated) basins with continuous
daily records spanning 1990-01-01 to 2023-12-31.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import CHUNK01_DIR
from source.utils.logging_config import get_logger

logger = get_logger("select_pilot_panel")

# Curated pilot panel: 18 USGS stations with verified GAGES-II classification,
# active 1990-2023 record, and diverse drainage areas and HUC regions.
PILOT_GAUGES_DATA: List[Dict[str, Any]] = [
    {
        "site_no": "01372500",
        "station_name": "Wappinger Creek near Wappingers Falls, NY",
        "huc_region": "02",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 181.0,
        "record_start": "1928-05-01",
        "record_end": "present",
        "selection_reason": "Northeast reference basin (CAMELS-US), HUC-02, long continuous record"
    },
    {
        "site_no": "01445500",
        "station_name": "Pequest River at Pequest, NJ",
        "huc_region": "02",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 106.0,
        "record_start": "1921-11-01",
        "record_end": "present",
        "selection_reason": "Mid-Atlantic reference basin (CAMELS-US), HUC-02, small catchment"
    },
    {
        "site_no": "01463500",
        "station_name": "Delaware River at Trenton, NJ",
        "huc_region": "02",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 6780.0,
        "record_start": "1912-10-01",
        "record_end": "present",
        "selection_reason": "Large regulated basin, HUC-02, major NWPS flood forecasting point"
    },
    {
        "site_no": "01646500",
        "station_name": "Potomac River near Washington, DC Little Falls",
        "huc_region": "02",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 11560.0,
        "record_start": "1930-03-01",
        "record_end": "present",
        "selection_reason": "Large regulated basin, HUC-02, major metropolitan NWPS flood point"
    },
    {
        "site_no": "02083500",
        "station_name": "Tar River at Tarboro, NC",
        "huc_region": "03",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 2183.0,
        "record_start": "1896-12-01",
        "record_end": "present",
        "selection_reason": "Southeast coastal plain non-ref basin, HUC-03, high historical flood frequency"
    },
    {
        "site_no": "02085000",
        "station_name": "Eno River near Durham, NC",
        "huc_region": "03",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 141.0,
        "record_start": "1963-11-01",
        "record_end": "present",
        "selection_reason": "Piedmont reference basin (CAMELS-US), HUC-03, moderate drainage area"
    },
    {
        "site_no": "02322500",
        "station_name": "Santa Fe River near Fort White, FL",
        "huc_region": "03",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 1017.0,
        "record_start": "1927-10-01",
        "record_end": "present",
        "selection_reason": "Karst/subtropical reference basin (CAMELS-US), HUC-03"
    },
    {
        "site_no": "03335500",
        "station_name": "Wabash River at Lafayette, IN",
        "huc_region": "05",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 7267.0,
        "record_start": "1901-05-01",
        "record_end": "present",
        "selection_reason": "Midwest agricultural regulated basin, HUC-05, prominent NWPS river forecast point"
    },
    {
        "site_no": "03345500",
        "station_name": "Embarras River at Ste. Marie, IL",
        "huc_region": "05",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 1516.0,
        "record_start": "1909-10-01",
        "record_end": "present",
        "selection_reason": "Midwest agricultural reference basin (CAMELS-US), HUC-05"
    },
    {
        "site_no": "05420500",
        "station_name": "Mississippi River at Clinton, IA",
        "huc_region": "07",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 85600.0,
        "record_start": "1873-06-01",
        "record_end": "present",
        "selection_reason": "Continental-scale regulated mainstem, HUC-07, key NWPS major flood point"
    },
    {
        "site_no": "05431486",
        "station_name": "Turtle Creek at Carvers Rock Road near Clinton, WI",
        "huc_region": "07",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 199.0,
        "record_start": "1939-09-01",
        "record_end": "present",
        "selection_reason": "Upper Mississippi tributary non-ref basin, HUC-07"
    },
    {
        "site_no": "05435500",
        "station_name": "Pecatonica River at Freeport, IL",
        "huc_region": "07",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 1327.0,
        "record_start": "1914-09-01",
        "record_end": "present",
        "selection_reason": "Upper Mississippi reference basin (CAMELS-US), HUC-07"
    },
    {
        "site_no": "06805500",
        "station_name": "Platte River at Louisville, NE",
        "huc_region": "10",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 85370.0,
        "record_start": "1953-05-01",
        "record_end": "present",
        "selection_reason": "Missouri basin regulated sand-bed river, HUC-10, NWPS flood point"
    },
    {
        "site_no": "06888500",
        "station_name": "Mill Creek near Paxico, KS",
        "huc_region": "10",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 318.0,
        "record_start": "1953-12-01",
        "record_end": "present",
        "selection_reason": "Great Plains grassland reference basin (CAMELS-US), HUC-10"
    },
    {
        "site_no": "08167000",
        "station_name": "Guadalupe River at Comfort, TX",
        "huc_region": "12",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 839.0,
        "record_start": "1939-05-01",
        "record_end": "present",
        "selection_reason": "Texas Hill Country flash-flood prone basin, HUC-12, NWPS rapid rise point"
    },
    {
        "site_no": "08167500",
        "station_name": "Guadalupe River near Spring Branch, TX",
        "huc_region": "12",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 1315.0,
        "record_start": "1922-06-01",
        "record_end": "present",
        "selection_reason": "Texas Hill Country reference basin (CAMELS-US), HUC-12"
    },
    {
        "site_no": "14137000",
        "station_name": "Sandy River near Marmot, OR",
        "huc_region": "17",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 264.0,
        "record_start": "1911-08-01",
        "record_end": "present",
        "selection_reason": "Pacific Northwest snow-influenced reference basin (CAMELS-US), HUC-17"
    },
    {
        "site_no": "14211720",
        "station_name": "Willamette River at Portland, OR",
        "huc_region": "17",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 11200.0,
        "record_start": "1972-10-01",
        "record_end": "present",
        "selection_reason": "Pacific Northwest large regulated river, HUC-17, major NWPS tidal/flood point"
    }
]


def build_stratification_summary(gauges: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute summary statistics across the selected gauge panel."""
    ref_count = sum(1 for g in gauges if g["gagesii_class"] == "Ref")
    non_ref_count = sum(1 for g in gauges if g["gagesii_class"] == "Non-Ref")
    huc_regions = sorted(list({g["huc_region"] for g in gauges}))
    areas = [g["drainage_area_sqmi"] for g in gauges if g.get("drainage_area_sqmi") is not None]
    min_area = min(areas) if areas else 0.0
    max_area = max(areas) if areas else 0.0

    return {
        "total_gauges": len(gauges),
        "reference_count": ref_count,
        "non_reference_count": non_ref_count,
        "huc_regions_represented": huc_regions,
        "drainage_area_range_sqmi": [round(min_area, 1), round(max_area, 1)]
    }


def build_pilot_panel_manifest(output_path: Path) -> Path:
    """Build and write the pilot panel JSON manifest."""
    stratification = build_stratification_summary(PILOT_GAUGES_DATA)

    payload = {
        "panel_id": "pilot_v1",
        "selection_date": "2026-08-17",
        "gauges": PILOT_GAUGES_DATA,
        "stratification_summary": stratification
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    logger.info(
        f"Pilot panel manifest written to {output_path} with {len(PILOT_GAUGES_DATA)} gauges "
        f"across {len(stratification['huc_regions_represented'])} HUC regions."
    )
    return output_path


def main() -> None:
    target_path = CHUNK01_DIR / "pilot_panel.json"
    build_pilot_panel_manifest(target_path)


if __name__ == "__main__":
    main()
