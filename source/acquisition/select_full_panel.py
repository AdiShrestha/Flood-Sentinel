"""Full Gauge Panel Selection and Stratification (FR-004 / INV-004 / C02-03).

Constructs the finalized 54-streamgage full CONUS panel from GAGES-II and CAMELS-US,
incorporating all 18 pilot stations and stratifying across 14 HUC regions,
drainage area classes, reference vs. non-reference regimes, and climate zones.
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

from source.utils.config import CHUNK01_DIR, CHUNK02_DIR
from source.utils.logging_config import get_logger

logger = get_logger("select_full_panel")

# Complete panel of 54 stratified streamgages
FULL_PANEL_CANDIDATES: List[Dict[str, Any]] = [
    # --- 18 Pilot Stations (Continuity with Chunk 01) ---
    {
        "site_no": "01372500",
        "station_name": "Wappinger Creek near Wappingers Falls, NY",
        "huc_region": "02",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 181.0,
        "drainage_area_class": "medium",
        "koppen_climate": "Dfa",
        "snow_influenced": True,
        "in_pilot_panel": True,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Pilot panel station; Mid-Atlantic Hudson tributary with suburban development"
    },
    {
        "site_no": "01445500",
        "station_name": "Pequest River at Pequest, NJ",
        "huc_region": "02",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 106.0,
        "drainage_area_class": "medium",
        "koppen_climate": "Dfa",
        "snow_influenced": True,
        "in_pilot_panel": True,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Pilot panel station; Mid-Atlantic reference benchmark with limestone karst baseflow"
    },
    {
        "site_no": "01463500",
        "station_name": "Delaware River at Trenton, NJ",
        "huc_region": "02",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 6780.0,
        "drainage_area_class": "large",
        "koppen_climate": "Cfa",
        "snow_influenced": True,
        "in_pilot_panel": True,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Pilot panel station; Major Mid-Atlantic trunk river with multi-reservoir regulation"
    },
    {
        "site_no": "01646500",
        "station_name": "Potomac River near Washington, DC (Little Falls)",
        "huc_region": "02",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 11560.0,
        "drainage_area_class": "large",
        "koppen_climate": "Cfa",
        "snow_influenced": True,
        "in_pilot_panel": True,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Pilot panel station; Major eastern river with rain-on-snow flood history"
    },
    {
        "site_no": "02083500",
        "station_name": "Tar River at Tarboro, NC",
        "huc_region": "03",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 2183.0,
        "drainage_area_class": "large",
        "koppen_climate": "Cfa",
        "snow_influenced": False,
        "in_pilot_panel": True,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Pilot panel station; Coastal Plain hurricane flood vulnerability"
    },
    {
        "site_no": "02085000",
        "station_name": "Eno River near Durham, NC",
        "huc_region": "03",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 141.0,
        "drainage_area_class": "medium",
        "koppen_climate": "Cfa",
        "snow_influenced": False,
        "in_pilot_panel": True,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Pilot panel station; Piedmont reference benchmark in South Atlantic"
    },
    {
        "site_no": "02322500",
        "station_name": "Santa Fe River near Fort White, FL",
        "huc_region": "03",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 1017.0,
        "drainage_area_class": "large",
        "koppen_climate": "Cfa",
        "snow_influenced": False,
        "in_pilot_panel": True,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Pilot panel station; Low-gradient karst reference basin with spring-fed baseflow"
    },
    {
        "site_no": "03335500",
        "station_name": "Wabash River at Lafayette, IN",
        "huc_region": "05",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 7267.0,
        "drainage_area_class": "large",
        "koppen_climate": "Dfa",
        "snow_influenced": True,
        "in_pilot_panel": True,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Pilot panel station; Agricultural Ohio basin with tile drainage and spring snowmelt"
    },
    {
        "site_no": "03345500",
        "station_name": "Embarras River at Ste. Marie, IL",
        "huc_region": "05",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 1516.0,
        "drainage_area_class": "large",
        "koppen_climate": "Dfa",
        "snow_influenced": True,
        "in_pilot_panel": True,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Pilot panel station; Midwestern reference benchmark with agricultural land use"
    },
    {
        "site_no": "05420500",
        "station_name": "Mississippi River at Clinton, IA",
        "huc_region": "07",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 85600.0,
        "drainage_area_class": "large",
        "koppen_climate": "Dfa",
        "snow_influenced": True,
        "in_pilot_panel": True,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Pilot panel station; Continental-scale trunk river with lock-and-dam regulation"
    },
    {
        "site_no": "05431486",
        "station_name": "Brewery Creek at Cross Plains, WI",
        "huc_region": "07",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 8.5,
        "drainage_area_class": "small",
        "koppen_climate": "Dfb",
        "snow_influenced": True,
        "in_pilot_panel": True,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Pilot panel station; Driftless Area small headwater reference stream"
    },
    {
        "site_no": "05435500",
        "station_name": "Pecatonica River at Freeport, IL",
        "huc_region": "07",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 1326.0,
        "drainage_area_class": "large",
        "koppen_climate": "Dfa",
        "snow_influenced": True,
        "in_pilot_panel": True,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Pilot panel station; Upper Mississippi reference benchmark with frequent overbank floods"
    },
    {
        "site_no": "06805500",
        "station_name": "Platte River at Louisville, NE",
        "huc_region": "10",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 85300.0,
        "drainage_area_class": "large",
        "koppen_climate": "Dfa",
        "snow_influenced": True,
        "in_pilot_panel": True,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Pilot panel station; Great Plains braided sandbed river with major ice-jam/snowmelt floods"
    },
    {
        "site_no": "06888500",
        "station_name": "Mill Creek near Paxico, KS",
        "huc_region": "10",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 316.0,
        "drainage_area_class": "medium",
        "koppen_climate": "Dfa",
        "snow_influenced": True,
        "in_pilot_panel": True,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Pilot panel station; Flint Hills tallgrass prairie reference stream"
    },
    {
        "site_no": "08167000",
        "station_name": "Guadalupe River at Comfort, TX",
        "huc_region": "12",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 839.0,
        "drainage_area_class": "medium",
        "koppen_climate": "Cfa",
        "snow_influenced": False,
        "in_pilot_panel": True,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Pilot panel station; Texas Hill Country flash-flood alley reference gauge"
    },
    {
        "site_no": "08167500",
        "station_name": "Guadalupe River near Spring Branch, TX",
        "huc_region": "12",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 1315.0,
        "drainage_area_class": "large",
        "koppen_climate": "Cfa",
        "snow_influenced": False,
        "in_pilot_panel": True,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Pilot panel station; Flash-flood prone limestone canyon upstream of Canyon Lake"
    },
    {
        "site_no": "14137000",
        "station_name": "Sandy River near Marmot, OR",
        "huc_region": "17",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 262.0,
        "drainage_area_class": "medium",
        "koppen_climate": "Csb",
        "snow_influenced": True,
        "in_pilot_panel": True,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Pilot panel station; Glaciated Pacific Northwest volcanic basin"
    },
    {
        "site_no": "14211720",
        "station_name": "Willamette River at Portland, OR",
        "huc_region": "17",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 11100.0,
        "drainage_area_class": "large",
        "koppen_climate": "Csb",
        "snow_influenced": True,
        "in_pilot_panel": True,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Pilot panel station; Major regulated Pacific Northwest trunk river"
    },

    # --- 36 Scale Expansion Stations Across 14 HUC Regions ---
    # HUC 01 (New England)
    {
        "site_no": "01034500",
        "station_name": "Piscataquis River near Dover-Foxcroft, ME",
        "huc_region": "01",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 297.0,
        "drainage_area_class": "medium",
        "koppen_climate": "Dfb",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "New England northern forest reference benchmark"
    },
    {
        "site_no": "01137500",
        "station_name": "Ammonoosuc River at Bethlehem Junction, NH",
        "huc_region": "01",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 87.6,
        "drainage_area_class": "small",
        "koppen_climate": "Dfb",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "White Mountains alpine snowmelt headwater benchmark"
    },
    {
        "site_no": "01184000",
        "station_name": "Connecticut River at Thompsonville, CT",
        "huc_region": "01",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 9660.0,
        "drainage_area_class": "large",
        "koppen_climate": "Dfa",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Major regulated New England river trunk"
    },

    # HUC 02 (Mid-Atlantic)
    {
        "site_no": "01434000",
        "station_name": "Delaware River at Port Jervis, NY",
        "huc_region": "02",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 3070.0,
        "drainage_area_class": "large",
        "koppen_climate": "Dfb",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Upper Delaware River regulated basin with reservoir operations"
    },
    {
        "site_no": "01541000",
        "station_name": "West Branch Susquehanna River at Bower, PA",
        "huc_region": "02",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 315.0,
        "drainage_area_class": "medium",
        "koppen_climate": "Dfb",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Appalachian Plateau reference benchmark"
    },

    # HUC 03 (South Atlantic-Gulf)
    {
        "site_no": "02138500",
        "station_name": "Linville River near Nebo, NC",
        "huc_region": "03",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 66.7,
        "drainage_area_class": "small",
        "koppen_climate": "Cfa",
        "snow_influenced": False,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Blue Ridge steep headwater reference basin"
    },
    {
        "site_no": "02175000",
        "station_name": "Edisto River near Givhans, SC",
        "huc_region": "03",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 2725.0,
        "drainage_area_class": "large",
        "koppen_climate": "Cfa",
        "snow_influenced": False,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Coastal Plain blackwater river reference gauge"
    },
    {
        "site_no": "02202500",
        "station_name": "Ogeechee River near Eden, GA",
        "huc_region": "03",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 2650.0,
        "drainage_area_class": "large",
        "koppen_climate": "Cfa",
        "snow_influenced": False,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Southeast coastal swamp and floodplain reference system"
    },

    # HUC 04 (Great Lakes)
    {
        "site_no": "040851385",
        "station_name": "Kewaunee River near Kewaunee, WI",
        "huc_region": "04",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 128.0,
        "drainage_area_class": "medium",
        "koppen_climate": "Dfb",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Lake Michigan agricultural basin with severe snowmelt runoff"
    },
    {
        "site_no": "04122500",
        "station_name": "Pere Marquette River at Scottville, MI",
        "huc_region": "04",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 709.0,
        "drainage_area_class": "medium",
        "koppen_climate": "Dfb",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Michigan Lower Peninsula groundwater-dominated reference benchmark"
    },
    {
        "site_no": "04193500",
        "station_name": "Maumee River at Waterville, OH",
        "huc_region": "04",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 6330.0,
        "drainage_area_class": "large",
        "koppen_climate": "Dfa",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Lake Erie agricultural basin with severe nutrient and flash runoff"
    },

    # HUC 05 (Ohio)
    {
        "site_no": "03164000",
        "station_name": "New River at Glen Lyn, VA",
        "huc_region": "05",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 3768.0,
        "drainage_area_class": "large",
        "koppen_climate": "Cfa",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Ancient Appalachian gorge river with hydroelectric regulation"
    },
    {
        "site_no": "03217500",
        "station_name": "Tygart Valley River at Belington, WV",
        "huc_region": "05",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 408.0,
        "drainage_area_class": "medium",
        "koppen_climate": "Dfb",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Allegheny Mountains steep headwater reference basin"
    },

    # HUC 06 (Tennessee)
    {
        "site_no": "03438000",
        "station_name": "French Broad River at Marshall, NC",
        "huc_region": "06",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 1332.0,
        "drainage_area_class": "large",
        "koppen_climate": "Cfa",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Southern Appalachian mountain trunk river"
    },
    {
        "site_no": "03497300",
        "station_name": "Cataloochee Creek near Cataloochee, NC",
        "huc_region": "06",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 49.2,
        "drainage_area_class": "small",
        "koppen_climate": "Cfa",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Great Smoky Mountains pristine national park reference basin"
    },

    # HUC 07 (Upper Mississippi)
    {
        "site_no": "05286000",
        "station_name": "Rum River near St. Francis, MN",
        "huc_region": "07",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 1360.0,
        "drainage_area_class": "large",
        "koppen_climate": "Dfb",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Northern glacial lake-and-wetland reference stream"
    },
    {
        "site_no": "05389500",
        "station_name": "Black River near Galesville, WI",
        "huc_region": "07",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 2120.0,
        "drainage_area_class": "large",
        "koppen_climate": "Dfb",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Western Wisconsin forested and agricultural river with hydropower"
    },

    # HUC 08 (Lower Mississippi)
    {
        "site_no": "07288500",
        "station_name": "Yazoo River at Redwood, MS",
        "huc_region": "08",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 13120.0,
        "drainage_area_class": "large",
        "koppen_climate": "Cfa",
        "snow_influenced": False,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Mississippi Delta heavily regulated agricultural lowlands"
    },
    {
        "site_no": "07375500",
        "station_name": "Comite River near Olive Branch, LA",
        "huc_region": "08",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 145.0,
        "drainage_area_class": "medium",
        "koppen_climate": "Cfa",
        "snow_influenced": False,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Gulf coastal plain flash flood reference basin"
    },

    # HUC 10 (Missouri)
    {
        "site_no": "06025500",
        "station_name": "Big Hole River near Melrose, MT",
        "huc_region": "10",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 2470.0,
        "drainage_area_class": "large",
        "koppen_climate": "Dfb",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Northern Rocky Mountains snowmelt-dominated reference river"
    },
    {
        "site_no": "06478500",
        "station_name": "James River near Scotland, SD",
        "huc_region": "10",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 21550.0,
        "drainage_area_class": "large",
        "koppen_climate": "Dfa",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Northern Great Plains extremely low gradient prairie river"
    },
    {
        "site_no": "06719505",
        "station_name": "Clear Creek at Golden, CO",
        "huc_region": "10",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 392.0,
        "drainage_area_class": "medium",
        "koppen_climate": "BSk",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Colorado Front Range mountain-to-plains transition with diversions"
    },

    # HUC 11 (Arkansas-White-Red)
    {
        "site_no": "07144100",
        "station_name": "Little Arkansas River near Sedgwick, KS",
        "huc_region": "11",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 1239.0,
        "drainage_area_class": "large",
        "koppen_climate": "Cfa",
        "snow_influenced": False,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Southern Great Plains agricultural basin with intense thunderstorms"
    },
    {
        "site_no": "07197000",
        "station_name": "Baron Fork at Eldon, OK",
        "huc_region": "11",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 307.0,
        "drainage_area_class": "medium",
        "koppen_climate": "Cfa",
        "snow_influenced": False,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Ozark Plateau gravel-bed river reference benchmark"
    },
    {
        "site_no": "07261000",
        "station_name": "Buffalo River near St. Joe, AR",
        "huc_region": "11",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 829.0,
        "drainage_area_class": "medium",
        "koppen_climate": "Cfa",
        "snow_influenced": False,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Ozarks National River karst and canyon benchmark"
    },

    # HUC 12 (Texas-Gulf)
    {
        "site_no": "08068000",
        "station_name": "West Fork San Jacinto River near Conroe, TX",
        "huc_region": "12",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 845.0,
        "drainage_area_class": "medium",
        "koppen_climate": "Cfa",
        "snow_influenced": False,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Greater Houston urbanizing watershed with severe tropical flood events"
    },
    {
        "site_no": "08101000",
        "station_name": "San Gabriel River at Georgetown, TX",
        "huc_region": "12",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 415.0,
        "drainage_area_class": "medium",
        "koppen_climate": "Cfa",
        "snow_influenced": False,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Balcones Fault Zone flash-flood corridor"
    },
    {
        "site_no": "08144500",
        "station_name": "San Saba River at San Saba, TX",
        "huc_region": "12",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 3042.0,
        "drainage_area_class": "large",
        "koppen_climate": "BSk",
        "snow_influenced": False,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Edwards Plateau semi-arid flash-flood reference basin"
    },

    # HUC 14 (Upper Colorado)
    {
        "site_no": "09070500",
        "station_name": "Colorado River near Dotsero, CO",
        "huc_region": "14",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 4394.0,
        "drainage_area_class": "large",
        "koppen_climate": "BSk",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Upper Colorado alpine snowpack and trans-basin diversions near Dotsero"
    },
    {
        "site_no": "09112500",
        "station_name": "East River at Almont, CO",
        "huc_region": "14",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 289.0,
        "drainage_area_class": "medium",
        "koppen_climate": "Dfb",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Gunnison River alpine headwater snowmelt reference watershed"
    },

    # HUC 15 (Lower Colorado)
    {
        "site_no": "09444500",
        "station_name": "Gila River near Solomon, AZ",
        "huc_region": "15",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 7896.0,
        "drainage_area_class": "large",
        "koppen_climate": "BWh",
        "snow_influenced": False,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Southwestern arid desert canyon reference river"
    },
    {
        "site_no": "09498500",
        "station_name": "Salt River near Roosevelt, AZ",
        "huc_region": "15",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 4306.0,
        "drainage_area_class": "large",
        "koppen_climate": "BSk",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Mogollon Rim winter rain-on-snow and summer monsoon river"
    },

    # HUC 17 (Pacific Northwest)
    {
        "site_no": "12447200",
        "station_name": "Methow River near Pateros, WA",
        "huc_region": "17",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 1772.0,
        "drainage_area_class": "large",
        "koppen_climate": "Dfb",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "North Cascades snowmelt-dominated reference river"
    },
    {
        "site_no": "13317000",
        "station_name": "Salmon River at White Bird, ID",
        "huc_region": "17",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 13550.0,
        "drainage_area_class": "large",
        "koppen_climate": "Dfb",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Central Idaho wild and scenic river, largest undammed subbasin"
    },
    {
        "site_no": "14181500",
        "station_name": "North Santiam River at Niagara, OR",
        "huc_region": "17",
        "gagesii_class": "Non-Ref",
        "drainage_area_sqmi": 453.0,
        "drainage_area_class": "medium",
        "koppen_climate": "Csb",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Cascade Range volcanic watershed upstream of Detroit Dam"
    },

    # HUC 18 (California)
    {
        "site_no": "11264500",
        "station_name": "Merced River at Happy Isles Bridge near Yosemite, CA",
        "huc_region": "18",
        "gagesii_class": "Ref",
        "drainage_area_sqmi": 181.0,
        "drainage_area_class": "medium",
        "koppen_climate": "Csb",
        "snow_influenced": True,
        "in_pilot_panel": False,
        "record_start": "1990-01-01",
        "record_end": "2023-12-31",
        "selection_reason": "Sierra Nevada high-elevation granite reference basin"
    }
]


def execute_full_panel_selection() -> Path:
    """Select and serialize the 54-station full CONUS panel."""
    logger.info(f"Selecting full CONUS gauge panel with {len(FULL_PANEL_CANDIDATES)} streamgages...")

    # Stratification computation
    huc_counts: Dict[str, int] = {}
    ref_counts: Dict[str, int] = {"Ref": 0, "Non-Ref": 0}
    size_counts: Dict[str, int] = {"small": 0, "medium": 0, "large": 0}
    climate_counts: Dict[str, int] = {}
    snow_counts: Dict[str, int] = {"snow_influenced": 0, "snow_free": 0}

    for g in FULL_PANEL_CANDIDATES:
        huc = g["huc_region"]
        huc_counts[huc] = huc_counts.get(huc, 0) + 1

        cls = g["gagesii_class"]
        ref_counts[cls] = ref_counts.get(cls, 0) + 1

        sz = g["drainage_area_class"]
        size_counts[sz] = size_counts.get(sz, 0) + 1

        clim = g["koppen_climate"]
        climate_counts[clim] = climate_counts.get(clim, 0) + 1

        if g["snow_influenced"]:
            snow_counts["snow_influenced"] += 1
        else:
            snow_counts["snow_free"] += 1

    strat_summary = {
        "total_gauges": len(FULL_PANEL_CANDIDATES),
        "huc_regions_count": len(huc_counts),
        "huc_distribution": huc_counts,
        "reference_distribution": ref_counts,
        "drainage_area_distribution": size_counts,
        "climate_distribution": climate_counts,
        "snow_influence_distribution": snow_counts,
        "pilot_panel_retained_count": sum(1 for g in FULL_PANEL_CANDIDATES if g["in_pilot_panel"])
    }

    panel_payload = {
        "panel_id": "full_v1",
        "selection_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "total_gauges": len(FULL_PANEL_CANDIDATES),
        "gauges": FULL_PANEL_CANDIDATES,
        "stratification_summary": strat_summary
    }

    CHUNK02_DIR.mkdir(parents=True, exist_ok=True)
    out_file = CHUNK02_DIR / "full_panel.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(panel_payload, f, indent=2)

    logger.info(f"Full gauge panel successfully written to {out_file} ({len(FULL_PANEL_CANDIDATES)} gauges).")
    return out_file


def main() -> None:
    execute_full_panel_selection()


if __name__ == "__main__":
    main()
