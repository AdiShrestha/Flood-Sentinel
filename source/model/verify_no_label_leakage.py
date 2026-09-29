"""Verification script for Zero Label Leakage in Self-Supervised Pretraining (C04-04 / INV-001).

Performs static AST analysis and dynamic runtime inspection to ensure no flood event catalogs,
target exceedance labels, or downstream evaluation thresholds are touched during pretraining.
"""

import ast
import sys
from pathlib import Path
from typing import List

# Add project root to sys.path if running as standalone script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.model.pretrain_dataset import PHYSICAL_CHANNELS, HydroPretrainDataset
from source.utils.logging_config import get_logger

logger = get_logger("verify_no_label_leakage")

FORBIDDEN_TERMS = [
    "primary_flood_episodes",
    "flood_events",
    "flood_thresholds",
    "nssl_flash",
    "storm_events",
    "exceedance_label",
    "binary_target",
    "is_flood",
    "action_stage_ft",
    "minor_stage_ft",
    "moderate_stage_ft",
    "major_stage_ft"
]


def audit_ast_for_forbidden_terms(file_path: Path) -> List[str]:
    """Scan file AST and string literals for forbidden downstream label references."""
    errors = []
    if not file_path.exists():
        return errors  # Skipped if file not created yet

    text = file_path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(file_path))

    for node in ast.walk(tree):
        # Check string constants
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            val_lower = node.value.lower()
            for term in FORBIDDEN_TERMS:
                if term in val_lower:
                    errors.append(f"Forbidden term '{term}' found in string literal at {file_path.name}:{node.lineno}")
        # Check identifiers/names
        elif isinstance(node, ast.Name):
            name_lower = node.id.lower()
            for term in FORBIDDEN_TERMS:
                if term == name_lower:
                    errors.append(f"Forbidden variable/name '{term}' found at {file_path.name}:{node.lineno}")
        # Check attributes
        elif isinstance(node, ast.Attribute):
            attr_lower = node.attr.lower()
            for term in FORBIDDEN_TERMS:
                if term == attr_lower:
                    errors.append(f"Forbidden attribute '{term}' found at {file_path.name}:{node.lineno}")

    return errors


def validate_runtime_dataset() -> List[str]:
    """Inspect dataset instance at runtime for pure physical input channels."""
    errors = []
    dataset = HydroPretrainDataset(max_samples=5, precache=False)

    if len(PHYSICAL_CHANNELS) != 6:
        errors.append(f"Expected 6 physical channels, found {len(PHYSICAL_CHANNELS)}: {PHYSICAL_CHANNELS}")

    expected_channels = {
        "discharge_cfs",
        "gage_height_ft",
        "precipitation_mm",
        "temperature_min_degc",
        "temperature_max_degc",
        "swe_mm"
    }
    if set(PHYSICAL_CHANNELS) != expected_channels:
        errors.append(f"Physical channels mismatch: {set(PHYSICAL_CHANNELS)} vs {expected_channels}")

    # Check sample outputs
    x_masked, x_target, mask = dataset[0]
    if x_masked.shape != (365, 6) or x_target.shape != (365, 6) or mask.shape != (365, 6):
        errors.append(f"Output shapes invalid: x_masked={x_masked.shape}, x_target={x_target.shape}, mask={mask.shape}")

    return errors


def main() -> None:
    logger.info("Executing No-Label Leakage Structural Audit...")
    errors: List[str] = []

    model_files = [
        _PROJECT_ROOT / "source" / "model" / "pretrain_dataset.py",
        _PROJECT_ROOT / "source" / "model" / "c_encoder.py",
        _PROJECT_ROOT / "source" / "model" / "timing_pilot.py"
    ]

    for f_path in model_files:
        if f_path.exists():
            f_errs = audit_ast_for_forbidden_terms(f_path)
            errors.extend(f_errs)

    # Runtime dataset check
    dataset_errs = validate_runtime_dataset()
    errors.extend(dataset_errs)

    if errors:
        logger.error(f"No-Label Leakage Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)
    else:
        logger.info("No-Label Leakage Structural Audit PASSED (0 downstream event labels touched).")
        sys.exit(0)


if __name__ == "__main__":
    main()
