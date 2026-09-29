"""Manifest I/O and validation utilities.

Enforces schemas for data_manifest.json and acquisition_provenance.json
per factory_spec.md Section Reality Gate.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


DATA_MANIFEST_REQUIRED_KEYS = {
    "gap_rate_pct",
    "distribution_stats",
    "temporal_range",
    "sensors_present",
    "channel_schema",
    "provenance_chain",
}

CHANNEL_SCHEMA_REQUIRED_KEYS = {
    "column_order",
    "units",
    "physical_range",
}

PROVENANCE_REQUIRED_KEYS = {
    "source",
    "api_endpoint",
    "authentication_method",
    "query_parameters",
    "total_api_calls",
    "total_scenes_returned",
    "first_scene_date",
    "last_scene_date",
    "http_status_codes",
    "response_payload_hash",
    "downloaded_file_manifest",
    "execution_environment",
}


def validate_data_manifest(data: Dict[str, Any]) -> List[str]:
    """Validate a data_manifest dictionary against factory_spec.md schema.
    
    Returns a list of error strings (empty if valid).
    """
    errors: List[str] = []
    missing = DATA_MANIFEST_REQUIRED_KEYS - set(data.keys())
    if missing:
        errors.append(f"Missing required top-level keys in data_manifest: {sorted(missing)}")

    if "gap_rate_pct" in data:
        if not isinstance(data["gap_rate_pct"], (int, float)):
            errors.append("gap_rate_pct must be numeric")

    if "distribution_stats" in data:
        if not isinstance(data["distribution_stats"], dict):
            errors.append("distribution_stats must be a dict")

    if "temporal_range" in data:
        tr = data["temporal_range"]
        if not isinstance(tr, dict) or "start" not in tr or "end" not in tr:
            errors.append("temporal_range must be a dict with 'start' and 'end' keys")

    if "sensors_present" in data:
        if not isinstance(data["sensors_present"], list):
            errors.append("sensors_present must be a list")

    if "channel_schema" in data:
        cs = data["channel_schema"]
        if not isinstance(cs, dict):
            errors.append("channel_schema must be a dict")
        else:
            missing_cs = CHANNEL_SCHEMA_REQUIRED_KEYS - set(cs.keys())
            if missing_cs:
                errors.append(f"Missing channel_schema keys: {sorted(missing_cs)}")

    if "provenance_chain" in data:
        pc = data["provenance_chain"]
        if not isinstance(pc, dict):
            errors.append("provenance_chain must be a dict")
        else:
            for ch, info in pc.items():
                if not isinstance(info, dict):
                    errors.append(f"provenance_chain entry for '{ch}' must be a dict")
                    continue
                if "raw_product" not in info or "transformation_steps" not in info or "undocumented_step" not in info:
                    errors.append(f"provenance_chain entry for '{ch}' missing required keys")

    return errors


def validate_acquisition_provenance(data: Dict[str, Any]) -> List[str]:
    """Validate an acquisition_provenance dictionary against factory_spec.md schema.
    
    Returns a list of error strings (empty if valid).
    """
    errors: List[str] = []
    missing = PROVENANCE_REQUIRED_KEYS - set(data.keys())
    if missing:
        errors.append(f"Missing required keys in acquisition_provenance: {sorted(missing)}")

    if "http_status_codes" in data:
        if not isinstance(data["http_status_codes"], list):
            errors.append("http_status_codes must be a list of integers")

    if "downloaded_file_manifest" in data:
        if not isinstance(data["downloaded_file_manifest"], list):
            errors.append("downloaded_file_manifest must be a list of dicts")

    if "execution_environment" in data:
        if not isinstance(data["execution_environment"], dict):
            errors.append("execution_environment must be a dict")

    return errors


def write_data_manifest(
    output_path: Union[str, Path],
    manifest_data: Dict[str, Any],
    validate: bool = True,
) -> Path:
    """Write data_manifest.json enforcing factory_spec.md schema."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    if validate:
        errors = validate_data_manifest(manifest_data)
        if errors:
            raise ValueError(f"Invalid data_manifest schema for {target}:\n" + "\n".join(errors))

    with open(target, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, sort_keys=True)

    return target


def write_acquisition_provenance(
    output_path: Union[str, Path],
    provenance_data: Dict[str, Any],
    validate: bool = True,
) -> Path:
    """Write acquisition_provenance.json enforcing factory_spec.md schema."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    if validate:
        errors = validate_acquisition_provenance(provenance_data)
        if errors:
            raise ValueError(f"Invalid acquisition_provenance schema for {target}:\n" + "\n".join(errors))

    with open(target, "w", encoding="utf-8") as f:
        json.dump(provenance_data, f, indent=2, sort_keys=True)

    return target


def load_data_manifest(path: Union[str, Path]) -> Dict[str, Any]:
    """Load and parse data_manifest.json."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_acquisition_provenance(path: Union[str, Path]) -> Dict[str, Any]:
    """Load and parse acquisition_provenance.json."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
