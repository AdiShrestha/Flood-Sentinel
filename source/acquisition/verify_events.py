"""Verification script for Independent Flood Event Acquisition (C01-08).

Validates flood_events.json structure, Event-Truth Hierarchy enforcement,
cross-referencing metadata, and manifest schemas.
"""

import json
import sys
from pathlib import Path
from typing import List

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.config import CHUNK01_DATA_DIR, CHUNK01_DIR, CHUNK01_MANIFESTS_DIR
from source.utils.logging_config import get_logger
from source.utils.manifest import (
    load_acquisition_provenance,
    load_data_manifest,
    validate_acquisition_provenance,
    validate_data_manifest,
)

logger = get_logger("verify_events")

VALID_SOURCES = {"primary", "secondary", "contextual"}
VALID_THRESHOLDS = {"action", "minor", "moderate", "major"}


def validate_events_acquisition() -> List[str]:
    """Validate all C01-08 flood events acquisition outputs."""
    errors: List[str] = []

    events_file = CHUNK01_DATA_DIR / "events" / "flood_events.json"
    if not events_file.exists():
        return [f"flood_events.json missing at {events_file}"]

    # 1. Validate events JSON structure and Event-Truth Hierarchy
    try:
        with open(events_file, "r", encoding="utf-8") as f:
            events = json.load(f)

        if not isinstance(events, list):
            return ["flood_events.json must be a list of event objects"]

        if len(events) == 0:
            return ["flood_events.json is empty"]

        primary_count = 0
        secondary_count = 0
        contextual_count = 0

        for idx, evt in enumerate(events):
            src = evt.get("source")
            if src not in VALID_SOURCES:
                errors.append(f"Event #{idx} has invalid source tag: '{src}' (expected {VALID_SOURCES})")

            if src == "primary":
                primary_count += 1
                if not evt.get("site_no"):
                    errors.append(f"Primary event {evt.get('event_id')} missing site_no")
                thresh = evt.get("threshold_level")
                if thresh not in VALID_THRESHOLDS:
                    errors.append(f"Primary event {evt.get('event_id')} has invalid threshold_level: '{thresh}'")
                if evt.get("method") != "usgs_nwps_crossing":
                    errors.append(f"Primary event {evt.get('event_id')} has non-USGS method: '{evt.get('method')}'")

            elif src == "secondary":
                secondary_count += 1
                if evt.get("method") != "nssl_flash":
                    errors.append(f"Secondary event {evt.get('event_id')} has invalid method: '{evt.get('method')}'")

            elif src == "contextual":
                contextual_count += 1
                if evt.get("method") != "noaa_storm_events":
                    errors.append(f"Contextual event {evt.get('event_id')} has invalid method: '{evt.get('method')}'")

        if primary_count == 0:
            errors.append("No primary-truth USGS crossing events found in catalog")

        logger.info(
            f"Event catalog composition: {primary_count} primary, "
            f"{secondary_count} secondary, {contextual_count} contextual events."
        )

    except Exception as e:
        errors.append(f"Failed to read flood_events.json: {e}")

    # 2. Validate data_manifest.json
    manifest_path = CHUNK01_MANIFESTS_DIR / "events_data_manifest.json"
    if not manifest_path.exists():
        errors.append(f"Manifest missing: {manifest_path}")
    else:
        try:
            manifest = load_data_manifest(manifest_path)
            errors.extend(validate_data_manifest(manifest))

            pc = manifest.get("provenance_chain", {})
            for ch_name, ch_info in pc.items():
                if ch_info.get("undocumented_step") is not False:
                    errors.append(f"Channel '{ch_name}' has undocumented_step != False")

        except Exception as e:
            errors.append(f"Failed to validate events_data_manifest: {e}")

    # 3. Validate acquisition_provenance.json
    provenance_path = CHUNK01_MANIFESTS_DIR / "events_acquisition_provenance.json"
    if not provenance_path.exists():
        errors.append(f"Provenance missing: {provenance_path}")
    else:
        try:
            prov = load_acquisition_provenance(provenance_path)
            errors.extend(validate_acquisition_provenance(prov))

            status_codes = prov.get("http_status_codes", [])
            if 200 not in status_codes or any(sc != 200 for sc in status_codes):
                errors.append(f"Unexpected HTTP status codes in events provenance: {status_codes}")

        except Exception as e:
            errors.append(f"Failed to validate events_acquisition_provenance: {e}")

    return errors


def main() -> None:
    errors = validate_events_acquisition()
    if errors:
        logger.error(f"Events Acquisition Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("Events Acquisition Verification PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    main()
