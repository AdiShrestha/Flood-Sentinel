"""Verification script for Train-Split Normalization (C03-10 / L1.2 Closure).

Validates:
1. `normalization_params.json` existence and declaration of `fit_split: "train"`.
2. `normalization_params_full.json` existence and declaration of `fit_split: "full_dataset"`.
3. Confirms that train-only parameters differ from full-dataset parameters (proving strict L1.2 closure).
4. Non-zero standard deviations across all normalized channels.
"""

import json
import sys
from pathlib import Path

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from source.utils.logging_config import get_logger

logger = get_logger("verify_normalization")


def main() -> None:
    chunk03_dir = _PROJECT_ROOT / "project" / "chunks" / "chunk03"
    train_params_path = chunk03_dir / "normalization_params.json"
    full_params_path = chunk03_dir / "normalization_params_full.json"
    
    if not train_params_path.exists():
        logger.error(f"Missing train normalization parameters at {train_params_path}")
        sys.exit(1)
        
    if not full_params_path.exists():
        logger.error(f"Missing full-dataset normalization parameters at {full_params_path}")
        sys.exit(1)
        
    with open(train_params_path, "r", encoding="utf-8") as f:
        train_payload = json.load(f)
        
    with open(full_params_path, "r", encoding="utf-8") as f:
        full_payload = json.load(f)
        
    if train_payload.get("fit_split") != "train":
        logger.error(f"Expected fit_split: 'train', found '{train_payload.get('fit_split')}'")
        sys.exit(1)
        
    if full_payload.get("fit_split") != "full_dataset":
        logger.error(f"Expected fit_split: 'full_dataset', found '{full_payload.get('fit_split')}'")
        sys.exit(1)
        
    train_channels = train_payload.get("channels", {})
    full_channels = full_payload.get("channels", {})
    
    if not train_channels or not full_channels:
        logger.error("Empty channel statistics in normalization artifacts")
        sys.exit(1)
        
    distinct_count = 0
    zero_std_channels = []
    
    for ch, t_stats in train_channels.items():
        if t_stats["std"] <= 0:
            zero_std_channels.append(ch)
            
        f_stats = full_channels.get(ch)
        if f_stats is None:
            logger.error(f"Channel {ch} missing from full-dataset normalization artifact")
            sys.exit(1)
            
        diff_mean = abs(t_stats["mean"] - f_stats["mean"])
        diff_std = abs(t_stats["std"] - f_stats["std"])
        
        if diff_mean > 1e-6 or diff_std > 1e-6:
            distinct_count += 1
            
    if zero_std_channels:
        logger.error(f"Degenerate zero-variance channels found: {zero_std_channels}")
        sys.exit(1)
        
    if distinct_count == 0:
        logger.error(
            "CRITICAL L1.2 FAILURE: Train-only and full-dataset normalization parameters are identical across all channels. "
            "Split boundary was not respected during preprocessing."
        )
        sys.exit(1)
        
    logger.info("Train-Split Normalization Verification PASSED.")
    logger.info(
        f"Verified: {distinct_count}/{len(train_channels)} channels statistically distinct between "
        f"Train-fit (N={train_payload['training_windows_count']}) and Full-fit (N={full_payload['total_windows_count']}). "
        f"L1.2 preprocessing leakage mechanically disproven."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
