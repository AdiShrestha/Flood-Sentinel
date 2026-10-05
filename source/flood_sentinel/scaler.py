"""Train-only scaler persistence and frozen normalization.

Enforces strict separation between training-set distribution fitting and evaluation-time
transformation. Prohibits fitting scalers on validation or test splits.
Adheres to Factory Principle C03, C14, and plan.md Section 6.1.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Sequence
import numpy as np
import torch

from flood_sentinel.preprocessing import Normalizer


class FitOnlyOnTrainError(ValueError):
    """Raised when an attempt is made to fit scaling parameters on non-training data."""
    pass


@dataclass(frozen=True)
class ScalerMetadata:
    """Metadata certifying the provenance of fitted normalization parameters."""
    split: str
    channel_names: tuple[str, ...]
    fitted_at_utc: str
    raw_training_sha256: str
    num_samples: int
    num_observations_per_channel: tuple[int, ...]


class PersistentScaler:
    """Persistent wrapper around Normalizer enforcing train-only fitting and immutability."""

    def __init__(self, normalizer: Normalizer, metadata: ScalerMetadata) -> None:
        if metadata.split != "train":
            raise FitOnlyOnTrainError(
                f"PersistentScaler cannot be initialized with split '{metadata.split}'. "
                "Normalization parameters must derive exclusively from the 'train' split."
            )
        self.normalizer = normalizer
        self.metadata = metadata

    @classmethod
    def fit(
        cls,
        raw_values: np.ndarray,
        channel_names: Sequence[str],
        *,
        split: str,
    ) -> PersistentScaler:
        """Fit normalization parameters strictly on declared raw training observations.

        Fails closed with FitOnlyOnTrainError if split != 'train'.
        """
        if split != "train":
            raise FitOnlyOnTrainError(
                f"Attempted to fit scaler on split '{split}'. Scalers must strictly "
                "be fitted on declared 'train' observations to prevent transductive leakage."
            )
        if raw_values.ndim != 2:
            raise ValueError(f"Expected 2D matrix of shape (observations, channels), got ndim={raw_values.ndim}")
        if raw_values.shape[1] != len(channel_names):
            raise ValueError(
                f"Channel count mismatch: array has {raw_values.shape[1]} channels, "
                f"names list has {len(channel_names)}"
            )

        # Compute cryptographic hash of training values for provenance tracking
        # Convert finite floats to bytes for hashing
        clean_bytes = np.nan_to_num(raw_values, nan=-999999.0).astype(np.float64).tobytes()
        train_hash = hashlib.sha256(clean_bytes).hexdigest()

        # Fit underlying domain normalizer
        normalizer = Normalizer.fit(raw_values, split="train")

        metadata = ScalerMetadata(
            split="train",
            channel_names=tuple(channel_names),
            fitted_at_utc=datetime.now(timezone.utc).isoformat(),
            raw_training_sha256=train_hash,
            num_samples=raw_values.shape[0],
            num_observations_per_channel=tuple(int(c) for c in normalizer.count),
        )
        return cls(normalizer, metadata)

    def transform(
        self,
        values: np.ndarray | torch.Tensor,
    ) -> tuple[np.ndarray | torch.Tensor, np.ndarray | torch.Tensor]:
        """Apply frozen normalization without updating parameters.

        Accepts either NumPy ndarray or PyTorch Tensor.
        Returns (scaled_values, observed_mask).
        """
        is_torch = isinstance(values, torch.Tensor)
        device = values.device if is_torch else None
        dtype = values.dtype if is_torch else None

        arr = values.detach().cpu().numpy() if is_torch else values
        scaled, mask = self.normalizer.transform(arr)

        if is_torch:
            scaled_t = torch.from_numpy(scaled).to(device=device, dtype=dtype)
            mask_t = torch.from_numpy(mask).to(device=device, dtype=torch.bool)
            return scaled_t, mask_t
        return scaled, mask

    def save(self, filepath: Path) -> None:
        """Serialize fitted parameters and metadata to JSON file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "metadata": {
                "split": self.metadata.split,
                "channel_names": list(self.metadata.channel_names),
                "fitted_at_utc": self.metadata.fitted_at_utc,
                "raw_training_sha256": self.metadata.raw_training_sha256,
                "num_samples": self.metadata.num_samples,
                "num_observations_per_channel": list(self.metadata.num_observations_per_channel),
            },
            "parameters": {
                "mean": self.normalizer.mean.tolist(),
                "scale": self.normalizer.scale.tolist(),
                "median": self.normalizer.median.tolist(),
                "count": self.normalizer.count.tolist(),
            },
        }
        filepath.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, filepath: Path) -> PersistentScaler:
        """Load and certify persisted normalization parameters."""
        if not filepath.is_file():
            raise FileNotFoundError(f"Scaler parameter file not found: {filepath}")

        data = json.loads(filepath.read_text(encoding="utf-8"))
        meta_dict = data["metadata"]
        param_dict = data["parameters"]

        if meta_dict["split"] != "train":
            raise FitOnlyOnTrainError(
                f"Persisted scaler has invalid split '{meta_dict['split']}'. Expected 'train'."
            )

        mean = np.array(param_dict["mean"], dtype=np.float64)
        scale = np.array(param_dict["scale"], dtype=np.float64)
        median = np.array(param_dict["median"], dtype=np.float64)
        count = np.array(param_dict["count"], dtype=np.int64)

        normalizer = Normalizer(mean=mean, scale=scale, median=median, count=count)

        metadata = ScalerMetadata(
            split=meta_dict["split"],
            channel_names=tuple(meta_dict["channel_names"]),
            fitted_at_utc=meta_dict["fitted_at_utc"],
            raw_training_sha256=meta_dict["raw_training_sha256"],
            num_samples=meta_dict["num_samples"],
            num_observations_per_channel=tuple(meta_dict["num_observations_per_channel"]),
        )
        return cls(normalizer, metadata)
