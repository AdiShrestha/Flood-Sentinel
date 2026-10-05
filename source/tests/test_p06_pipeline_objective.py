"""Unit and integration tests for data pipeline, missingness, and model objectives.

Verifies:
1. Future perturbation invariance across both dataset loaders and causal neural architectures.
2. Hidden-target withholding via forward hooks and zero input gradients.
3. Explicit distinction between missing values and observed zero measurements.
4. Finite loss and non-zero parameter gradients on authentic development batches.
5. PersistentScaler train-only fitting, JSON serialization fidelity, and parameter immutability.
6. Corruption generator mask invariants across random, channel, span, and mixed modes.
7. Score A (leave-channel-out residual) and Score B (fitted latent reference distance) calculations.
"""
from pathlib import Path
import tempfile
import numpy as np
import pytest
import torch

from flood_sentinel.adapters.availability import CausalLeakageError
from flood_sentinel.dataset import (
    CausalHydroDataset,
    collate_causal_batch,
    create_dataloader,
    parse_compact_issue_time,
)
from flood_sentinel.model import CausalForecastingHead, CausalHydroEncoder
from flood_sentinel.reconstruction import (
    CorruptionConfig,
    MaskedHydroModel,
    audit_observation_coverage,
    compute_score_a,
    compute_score_b,
    fit_latent_reference,
    leave_channel_out_score,
    sample_corruption_mask,
)
from flood_sentinel.scaler import FitOnlyOnTrainError, PersistentScaler
from flood_sentinel.scoring import LatentReference


COHORT_PATH = Path("data/cohort.csv")
SOURCE_RECORDS_PATH = Path("data/source_records.csv")


# ---------------------------------------------------------------------------
# 1. Future Perturbation Invariance Tests
# ---------------------------------------------------------------------------

def test_dataset_rejects_future_observations_beyond_issue_time():
    """Availability adapter must trigger CausalLeakageError on post-issue timestamps."""
    dataset = CausalHydroDataset(COHORT_PATH, SOURCE_RECORDS_PATH, split="train", verify_adapters=True)
    assert len(dataset) > 0

    # Injecting a synthetic record timestamped after issue time must fail causality audit
    sample = dataset[0]
    issue_dt = parse_compact_issue_time(sample.sample_id)
    post_issue_rec = {
        "record_id": "USGS_01646500_gage_height_m_20990101T000000Z",
        "timestamp_utc": "2099-01-01T00:00:00Z",
        "parameter": "gage_height_m",
        "value_si": "3.5",
        "raw_sha256": "0" * 64,
        "provider": "USGS",
    }
    # FABRICATION-DISCLOSURE: Synthetic record used strictly to test post-issue leakage rejection
    with pytest.raises(CausalLeakageError):
        from flood_sentinel.adapters.availability import AvailabilityAdapter
        AvailabilityAdapter.audit_sample_causality(
            sample_id=sample.sample_id,
            issue_time_utc=issue_dt,
            source_records=[post_issue_rec],
            lookback_hours=24.0,
        )


def test_causal_encoder_temporal_future_perturbation_invariance():
    """Causal neural representations at time t must be bitwise invariant to future inputs at t' > t."""
    # FABRICATION-DISCLOSURE: Constructed tensor to verify causal masking arithmetic
    torch.manual_seed(42)
    B, T, C = 2, 16, 4
    encoder = CausalHydroEncoder(in_channels=C, d_model=16, tcn_layers=2, transformer_layers=2, n_heads=2, d_ff=32, dropout=0.0).eval()

    inputs = torch.randn(B, T, C, dtype=torch.float32, requires_grad=True)
    z_base = encoder(inputs)

    # Perturb inputs strictly at steps t >= 10
    perturbed_inputs = inputs.clone().detach()
    perturbed_inputs[:, 10:, :] += 50.0
    perturbed_inputs.requires_grad_(True)
    z_perturbed = encoder(perturbed_inputs)

    # Causal invariance: representation at all past and current steps t < 10 must be bitwise identical
    assert torch.equal(z_base[:, :10, :], z_perturbed[:, :10, :])

    # Gradient check: gradients of z[:, 5, :] with respect to future inputs at t >= 6 must be strictly zero
    encoder.zero_grad()
    loss_at_5 = z_base[:, 5, :].sum()
    loss_at_5.backward()
    grad_at_future = inputs.grad[:, 6:, :]
    assert torch.count_nonzero(grad_at_future) == 0


# ---------------------------------------------------------------------------
# 2. Hidden-Target Target Withholding & Gradient Tests
# ---------------------------------------------------------------------------

def test_hidden_target_withholding_via_hooks_and_input_gradients():
    """Confirm hidden targets are withheld from encoder input and have zero input gradient."""
    # FABRICATION-DISCLOSURE: Fixture tensor to test target withholding mechanics
    torch.manual_seed(101)
    model = MaskedHydroModel(2, d_model=16, tcn_layers=1, transformer_layers=1, n_heads=2, d_ff=32, dropout=0.0).eval()

    values = torch.tensor([[[1.5, 2.5], [3.5, 4.5], [5.5, 6.5]]], dtype=torch.float32, requires_grad=True)
    observed = torch.ones_like(values, dtype=torch.bool)
    hidden = torch.zeros_like(observed)
    hidden[0, 1, 0] = True  # Hide channel 0 at time step 1

    captured_inputs = []
    hook = model.encoder.register_forward_pre_hook(lambda m, args: captured_inputs.append(args[0].clone()))

    # First forward call
    loss1 = model.masked_loss(values, observed, hidden)

    # Change hidden target by +200.0
    perturbed_values = values.detach().clone()
    perturbed_values[hidden] += 200.0
    loss2 = model.masked_loss(perturbed_values, observed, hidden)
    hook.remove()

    # 1. Encoder received bitwise identical inputs despite target mutation
    assert torch.equal(captured_inputs[0], captured_inputs[1])

    # 2. Loss arithmetic reflects target difference
    assert loss1.item() != loss2.item()

    # 3. Input gradient at hidden position is identically zero
    grad = torch.autograd.grad(loss1, values)[0]
    assert grad[hidden].item() == 0.0

    # 4. Attempting to select missing values as targets must raise ValueError
    observed[0, 1, 0] = False
    with pytest.raises(ValueError, match="must not select missing values as targets"):
        model.masked_loss(values, observed, hidden)


# ---------------------------------------------------------------------------
# 3. Missingness vs. Observed Zero Distinction
# ---------------------------------------------------------------------------

def test_missingness_vs_observed_zero_produces_distinct_representations():
    """An authentic zero measurement (observed=True) must be distinguished from missing data (observed=False)."""
    # FABRICATION-DISCLOSURE: Constructed comparison fixture to verify indicator encoding
    model = MaskedHydroModel(1, d_model=8, tcn_layers=1, transformer_layers=1, n_heads=2, d_ff=16, dropout=0.0).eval()

    # Case A: Observed zero
    val_obs_zero = torch.tensor([[[0.0]]], dtype=torch.float32)
    vis_obs_zero = torch.tensor([[[True]]], dtype=torch.bool)
    zA, predA = model(val_obs_zero, vis_obs_zero)

    # Case B: Missing value imputed to zero
    val_missing = torch.tensor([[[0.0]]], dtype=torch.float32)
    vis_missing = torch.tensor([[[False]]], dtype=torch.bool)
    zB, predB = model(val_missing, vis_missing)

    # Latents and reconstructions must not be identical
    assert not torch.equal(zA, zB)
    assert not torch.equal(predA, predB)


def test_corruption_generator_never_masks_missing_entries():
    """Corruption generator must strictly sample M within O (M subset of O)."""
    # FABRICATION-DISCLOSURE: Fixture mask containing genuine missing entries
    observed = torch.tensor([
        [[True, False], [True, True], [False, False], [True, False]],
        [[False, True], [False, False], [True, True], [True, False]],
    ], dtype=torch.bool)

    for mode in ["random", "channel", "span", "mixed"]:
        hidden = sample_corruption_mask(observed, mode=mode, rate=0.3, span_length=2, seed=77)
        # Invariant 1: No missing values selected
        assert not (hidden & ~observed).any(), f"Mode {mode} selected unobserved positions as targets."
        # Invariant 2: At least one observed target selected
        assert (hidden & observed).any(), f"Mode {mode} produced an empty target mask."


# ---------------------------------------------------------------------------
# 4. Finite Loss and Gradients on Authentic Development Batch
# ---------------------------------------------------------------------------

def test_authentic_development_batch_has_finite_loss_and_non_zero_gradients():
    """Train loader consuming authentic cohort and source records must compute finite loss and non-zero grads."""
    train_ds = CausalHydroDataset(COHORT_PATH, SOURCE_RECORDS_PATH, split="train")
    raw_train = train_ds.get_raw_observations_matrix()
    scaler = PersistentScaler.fit(raw_train, channel_names=["gage_height_m", "discharge_cms"], split="train")

    scaled_ds = CausalHydroDataset(COHORT_PATH, SOURCE_RECORDS_PATH, split="train", scaler=scaler)
    loader = create_dataloader(scaled_ds, batch_size=2, shuffle=False)

    batch = next(iter(loader))
    values = batch["values"]
    observed = batch["observed"]

    hidden = sample_corruption_mask(observed, mode="random", rate=0.25, seed=123)
    coverage = audit_observation_coverage(observed, hidden)
    assert coverage.total_observations > 0
    assert coverage.total_masked > 0
    assert 0.0 < coverage.mask_coverage_ratio < 1.0

    model = MaskedHydroModel(2, d_model=16, tcn_layers=1, transformer_layers=1, n_heads=2, d_ff=32, dropout=0.0).train()
    loss = model.masked_loss(values, observed, hidden)

    assert torch.isfinite(loss)
    assert loss.item() > 0.0

    loss.backward()
    grad_counts = [torch.count_nonzero(p.grad).item() for p in model.parameters() if p.grad is not None]
    assert len(grad_counts) > 0
    assert all(c > 0 for c in grad_counts), "All model layers must receive non-zero gradients."


# ---------------------------------------------------------------------------
# 5. PersistentScaler Train-Only Enforcement & Immutability
# ---------------------------------------------------------------------------

def test_persistent_scaler_train_only_enforcement_and_serialization():
    """PersistentScaler must fail closed on non-train splits and round-trip losslessly through JSON."""
    raw_data = np.array([[1.0, 10.0], [2.0, 20.0], [3.0, 30.0]], dtype=np.float64)

    # 1. Prohibit fitting on non-train splits
    for bad_split in ["validation", "test", "holdout", "all"]:
        with pytest.raises(FitOnlyOnTrainError):
            PersistentScaler.fit(raw_data, ["gage_height_m", "discharge_cms"], split=bad_split)

    # 2. Fit on train split
    scaler = PersistentScaler.fit(raw_data, ["gage_height_m", "discharge_cms"], split="train")
    assert scaler.metadata.split == "train"
    assert len(scaler.metadata.raw_training_sha256) == 64

    # 3. Parameter immutability
    with pytest.raises(ValueError):
        scaler.normalizer.mean[0] = 999.0

    # 4. JSON serialization and loading
    with tempfile.TemporaryDirectory() as tmp_dir:
        save_path = Path(tmp_dir) / "scaler.json"
        scaler.save(save_path)
        assert save_path.is_file()

        loaded_scaler = PersistentScaler.load(save_path)
        assert loaded_scaler.metadata.split == "train"
        assert loaded_scaler.metadata.raw_training_sha256 == scaler.metadata.raw_training_sha256
        np.testing.assert_array_equal(loaded_scaler.normalizer.mean, scaler.normalizer.mean)
        np.testing.assert_array_equal(loaded_scaler.normalizer.scale, scaler.normalizer.scale)

        # 5. Transform outputs must be bitwise identical
        eval_arr = np.array([[2.0, 20.0]], dtype=np.float64)
        scaled_orig, mask_orig = scaler.transform(eval_arr)
        scaled_loaded, mask_loaded = loaded_scaler.transform(eval_arr)
        np.testing.assert_array_equal(scaled_orig, scaled_loaded)
        np.testing.assert_array_equal(mask_orig, mask_loaded)


# ---------------------------------------------------------------------------
# 6. Corruption Generator Invariants and Policies
# ---------------------------------------------------------------------------

def test_corruption_generator_modes_and_determinism():
    """Verify random, channel, span, and mixed corruption modes with seed determinism."""
    # FABRICATION-DISCLOSURE: Synthetic observation tensor for corruption mode testing
    observed = torch.ones((4, 20, 3), dtype=torch.bool)
    observed[:, :, 2] = False  # Channel 2 completely missing

    # Mode: channel
    ch_mask = sample_corruption_mask(observed, mode="channel", seed=99)
    assert not (ch_mask & ~observed).any()
    assert (ch_mask & observed).any()
    # Masked channel must be channel 0 or 1, never missing channel 2
    assert ch_mask[:, :, 2].sum().item() == 0

    # Mode: span
    span_mask = sample_corruption_mask(observed, mode="span", span_length=5, seed=99)
    assert not (span_mask & ~observed).any()
    assert (span_mask & observed).any()
    assert span_mask[:, :, 2].sum().item() == 0

    # Determinism check
    mask1 = sample_corruption_mask(observed, mode="random", rate=0.2, seed=42)
    mask2 = sample_corruption_mask(observed, mode="random", rate=0.2, seed=42)
    assert torch.equal(mask1, mask2)

    # Invalid rate and span
    with pytest.raises(ValueError):
        sample_corruption_mask(observed, rate=0.0)
    with pytest.raises(ValueError):
        sample_corruption_mask(observed, rate=1.0)
    with pytest.raises(ValueError):
        sample_corruption_mask(observed, span_length=0)


# ---------------------------------------------------------------------------
# 7. Score A and Score B Anomaly Scorers
# ---------------------------------------------------------------------------

def test_score_a_leave_channel_out_evaluations():
    """Score A must compute leave-channel-out cross-reconstruction residuals under eval mode."""
    # FABRICATION-DISCLOSURE: Synthetic tensor for scoring API validation
    torch.manual_seed(55)
    model = MaskedHydroModel(2, d_model=8, tcn_layers=1, transformer_layers=1, n_heads=2, d_ff=16, dropout=0.0).eval()

    values = torch.randn(2, 10, 2, dtype=torch.float32)
    observed = torch.ones_like(values, dtype=torch.bool)

    # Training mode must fail
    model.train()
    with pytest.raises(ValueError, match="Scoring requires eval mode"):
        compute_score_a(model, values, observed)
    model.eval()

    # Aggregations
    mean_score = compute_score_a(model, values, observed, aggregation="mean")
    tail_score = compute_score_a(model, values, observed, aggregation="tail")
    max_score = compute_score_a(model, values, observed, aggregation="max")
    none_score = compute_score_a(model, values, observed, aggregation="none")

    assert mean_score.shape == (2,)
    assert tail_score.shape == (2,)
    assert max_score.shape == (2,)
    assert none_score.shape == (2, 10)
    assert torch.isfinite(mean_score).all()
    assert torch.isfinite(tail_score).all()
    assert (mean_score >= 0.0).all()


def test_score_b_latent_reference_fitting_and_distance():
    """Score B must fit LatentReference strictly on train and compute Mahalanobis distances."""
    train_ds = CausalHydroDataset(COHORT_PATH, SOURCE_RECORDS_PATH, split="train")
    raw_train = train_ds.get_raw_observations_matrix()
    scaler = PersistentScaler.fit(raw_train, ["gage_height_m", "discharge_cms"], split="train")
    train_ds_scaled = CausalHydroDataset(COHORT_PATH, SOURCE_RECORDS_PATH, split="train", scaler=scaler)
    loader = create_dataloader(train_ds_scaled, batch_size=2)

    model = MaskedHydroModel(2, d_model=16, tcn_layers=1, transformer_layers=1, n_heads=2, d_ff=32, dropout=0.0).eval()

    # Prohibit fitting reference on validation
    with pytest.raises(ValueError, match="cannot be fitted on split 'validation'"):
        fit_latent_reference(model, loader, split="validation")

    # Fit on train split
    ref = fit_latent_reference(model, loader, split="train", shrinkage=0.2)
    assert isinstance(ref, LatentReference)
    assert ref.mean.shape == (16,)
    assert ref.cholesky.shape == (16, 16)

    # Compute distances on train batch
    batch = next(iter(loader))
    distances = compute_score_b(model, batch["values"], batch["observed"], ref)
    assert distances.shape == (2,)
    assert np.isfinite(distances).all()
    assert (distances >= 0.0).all()


# ---------------------------------------------------------------------------
# 8. Causal Forecasting Head Verification
# ---------------------------------------------------------------------------

def test_causal_forecasting_head_forward_and_backward():
    """Verify CausalForecastingHead correctly projects issue-time latents and propagates gradients."""
    # FABRICATION-DISCLOSURE: Synthetic latent tensor to test head output shape and grad flow
    torch.manual_seed(88)
    head = CausalForecastingHead(d_model=16, out_dim=2)

    # 3D latent tensor: (B, T, D)
    latents = torch.randn(3, 10, 16, dtype=torch.float32, requires_grad=True)
    out = head(latents)
    assert out.shape == (3, 2)
    assert torch.isfinite(out).all()

    loss = out.sum()
    loss.backward()
    # Gradient flows strictly to the final time step t = -1
    assert torch.count_nonzero(latents.grad[:, -1, :]) > 0
    assert torch.count_nonzero(latents.grad[:, :-1, :]) == 0
