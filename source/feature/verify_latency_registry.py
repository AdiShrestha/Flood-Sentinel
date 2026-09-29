"""Verification script for Source Publication Latency Registry (C03-04).

Validates that latency_registry.json contains all required source channels,
proper non-negative latencies or 'N/A', non-empty descriptions, and valid citations.
"""

import json
import sys
from pathlib import Path
from typing import List

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.logging_config import get_logger

logger = get_logger("verify_latency_registry")


def validate_latency_registry() -> List[str]:
    """Validate source publication latency registry content."""
    errors: List[str] = []

    registry_path = _PROJECT_ROOT / "source" / "feature" / "latency_registry.json"
    if not registry_path.exists():
        return [f"latency_registry.json missing at {registry_path}"]

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
    except Exception as e:
        return [f"Failed to parse latency_registry.json: {e}"]

    required_channels = [
        "usgs_discharge",
        "usgs_gage_height",
        "gridmet_pr",
        "gridmet_tmmn",
        "gridmet_tmmx",
        "snodas_swe",
        "nwm_retro_discharge",
        "basin_attributes"
    ]

    for chan in required_channels:
        if chan not in registry:
            errors.append(f"Required channel '{chan}' missing from latency registry")
            continue

        entry = registry[chan]
        lat = entry.get("latency_hours")
        if lat != "N/A":
            if not isinstance(lat, (int, float)) or lat < 0:
                errors.append(f"Channel '{chan}' has invalid latency_hours: {lat}")

        desc = entry.get("latency_description", "")
        if not isinstance(desc, str) or not desc.strip():
            errors.append(f"Channel '{chan}' has empty latency_description")

        cite = entry.get("citation", "")
        if not isinstance(cite, str) or not cite.strip():
            errors.append(f"Channel '{chan}' has empty citation")

    return errors


def main() -> None:
    errors = validate_latency_registry()
    if errors:
        logger.error(f"Latency Registry Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("Source Publication Latency Registry Verification PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    main()
