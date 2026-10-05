"""Unit tests for development pilots, comparator ladder, and hardware profiling."""
from __future__ import annotations

from pathlib import Path
import time
import pytest
import numpy as np
import torch

from flood_sentinel.dataset import CausalHydroDataset, create_dataloader
from flood_sentinel.pilots import (
    EALSTMPilotTrainer,
    EWMACUSUMComparator,
    HardwareProfile,
    MaskedHydroPilotTrainer,
    PersistenceComparator,
    TabularRidgeComparator,
    measure_hardware_profile,
)
from flood_sentinel.scaler import PersistentScaler


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def train_dataset(repo_root: Path) -> CausalHydroDataset:
    cohort_path = repo_root / "data/cohort.csv"
    src_path = repo_root / "data/source_records.csv"
    raw_ds = CausalHydroDataset(cohort_path, src_path, split="train")
    scaler = PersistentScaler.fit(raw_ds.get_raw_observations_matrix(), raw_ds.channels, split="train")
    return CausalHydroDataset(cohort_path, src_path, split="train", scaler=scaler)


@pytest.fixture
def val_dataset(repo_root: Path, train_dataset: CausalHydroDataset) -> CausalHydroDataset:
    cohort_path = repo_root / "data/cohort.csv"
    src_path = repo_root / "data/source_records.csv"
    return CausalHydroDataset(cohort_path, src_path, split="validation", scaler=train_dataset.scaler)


# =========================================================================
# 1. Persistence Comparator Tests
# =========================================================================

def test_persistence_comparator(val_dataset: CausalHydroDataset):
    scores = PersistenceComparator.evaluate_dataset(val_dataset)
    assert len(scores) == len(val_dataset)
    assert all(isinstance(s, float) and np.isfinite(s) for s in scores)

    # Individual sample extraction
    s0 = val_dataset[0]
    score_0 = PersistenceComparator.evaluate_sample(s0)
    assert np.isfinite(score_0)


# =========================================================================
# 2. EWMA-CUSUM Comparator Tests
# =========================================================================

def test_ewma_cusum_comparator(train_dataset: CausalHydroDataset, val_dataset: CausalHydroDataset):
    model = EWMACUSUMComparator.fit_from_dataset(train_dataset, alpha=0.2, slack=0.5)
    assert np.isfinite(model.mean)
    assert model.scale > 0

    scores = model.evaluate_dataset(val_dataset)
    assert len(scores) == len(val_dataset)
    assert all(isinstance(s, float) and s >= 0.0 and np.isfinite(s) for s in scores)


# =========================================================================
# 3. Tabular Ridge Comparator Tests
# =========================================================================

def test_tabular_ridge_comparator(train_dataset: CausalHydroDataset, val_dataset: CausalHydroDataset):
    model = TabularRidgeComparator(l2_reg=1.0)
    # Cannot predict before fitting
    with pytest.raises(ValueError, match="must be fitted"):
        model.predict_proba(val_dataset[0])

    # Feature extraction check
    feats = model.extract_features(val_dataset[0])
    assert feats.shape == (10,)
    assert np.isfinite(feats).all()

    # Fit and predict
    model.fit(train_dataset)
    assert model.weights is not None
    assert len(model.weights) == 10

    scores = model.evaluate_dataset(val_dataset)
    assert len(scores) == len(val_dataset)
    assert all(0.0 <= s <= 1.0 for s in scores)


# =========================================================================
# 4. Supervised EA-LSTM Pilot Trainer Tests
# =========================================================================

def test_ea_lstm_pilot_trainer(train_dataset: CausalHydroDataset, val_dataset: CausalHydroDataset):
    train_loader = create_dataloader(train_dataset, batch_size=2, shuffle=True)
    val_loader = create_dataloader(val_dataset, batch_size=2, shuffle=False)

    trainer = EALSTMPilotTrainer(dynamic_dim=2, static_dim=4, hidden_dim=8, lr=1e-3)
    traces, meta, hw = trainer.train_pilot(
        train_loader, val_loader, max_epochs=3, patience=2, min_delta=1e-4
    )

    assert len(traces) >= 2  # Obey factory lifecycle rule (>= 2 epochs)
    assert "best_epoch" in meta
    assert meta["best_val_loss"] > 0
    assert hw.wall_clock_seconds > 0
    assert hw.peak_rss_mb > 0
    assert hw.total_parameters > 0

    # Predictions in [0, 1]
    scores = trainer.evaluate_dataset(val_loader)
    assert len(scores) == len(val_dataset)
    assert all(0.0 <= s <= 1.0 for s in scores)


# =========================================================================
# 5. Masked Hydro Pilot Trainer Tests
# =========================================================================

def test_masked_hydro_pilot_trainer(train_dataset: CausalHydroDataset, val_dataset: CausalHydroDataset):
    train_loader = create_dataloader(train_dataset, batch_size=2, shuffle=True)
    val_loader = create_dataloader(val_dataset, batch_size=2, shuffle=False)

    trainer = MaskedHydroPilotTrainer(
        in_channels=2, d_model=8, tcn_layers=1, transformer_layers=1, n_heads=1, lr=1e-3
    )
    traces, meta, hw = trainer.train_pilot(
        train_loader, val_loader, max_epochs=3, patience=2, corruption_rate=0.25
    )

    assert len(traces) >= 2
    assert meta["best_val_loss"] > 0
    assert hw.total_parameters > 0

    # Score A evaluation
    score_a = trainer.evaluate_score_a(val_loader)
    assert len(score_a) == len(val_dataset)
    assert all(isinstance(s, float) and np.isfinite(s) and s >= 0 for s in score_a)

    # Score B evaluation
    score_b = trainer.evaluate_score_b(train_loader, val_loader)
    assert len(score_b) == len(val_dataset)
    assert all(isinstance(s, float) and np.isfinite(s) and s >= 0 for s in score_b)


# =========================================================================
# 6. Hardware Measurement Profiler Tests
# =========================================================================

def test_hardware_profiler():
    t0 = time.perf_counter()
    time.sleep(0.01)
    dummy_model = torch.nn.Linear(10, 5)
    prof = measure_hardware_profile(t0, sample_count=100, model=dummy_model, device="cpu")

    assert prof.device == "cpu"
    assert prof.wall_clock_seconds >= 0.01
    assert prof.peak_rss_mb > 0.0
    assert prof.sample_count == 100
    assert prof.throughput_samples_per_sec > 0
    assert prof.total_parameters == (10 * 5 + 5)
