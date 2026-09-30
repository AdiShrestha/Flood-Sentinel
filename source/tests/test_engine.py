"""Engineering fixtures only. No test values may enter research evidence.

# FABRICATION-DISCLOSURE: all constructed arrays, IDs, observations and randomized
# tensors below are isolated test fixtures, never acquired hydrological data.
"""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import numpy as np
import pytest
import torch
from sklearn.metrics import roc_auc_score, average_precision_score

from flood_sentinel.temporal import Observation, as_of, OnsetInterval, future_event_label, first_persistent_alert
from flood_sentinel.preprocessing import Normalizer
from flood_sentinel.metrics import ranking_metrics, probability_metrics, holm, paired_cluster_interval
from flood_sentinel.scoring import RobustCalibration, LatentReference, latent_step_change
from flood_sentinel.model import CausalHydroEncoder, CausalMultiHeadAttention
from flood_sentinel.reconstruction import MaskedHydroModel, masked_observed_mse, leave_channel_out_score
from flood_sentinel.ea_lstm import EALSTMModel
from flood_sentinel.baselines import persistence_forecast, rate_of_change, ewma_cusum

T = datetime(2020, 1, 1, tzinfo=timezone.utc)


def observation(**changes):
    values = dict(record_id='fixture', provider='fixture', variable='rain', value=1., unit='mm',
                  observation_start=T, observation_end=T+timedelta(days=1),
                  available_at=T+timedelta(days=1, hours=14), availability_basis='observed', raw_sha256='a'*64)
    values.update(changes)
    return Observation(**values)


def test_availability_uses_issue_time_not_later_forecast_target():
    r = observation()
    assert as_of([r], T+timedelta(days=1)) == []
    assert as_of([r], r.available_at) == [r]


def test_unknown_or_assumed_vintage_cannot_become_operational():
    with pytest.raises(ValueError): as_of([observation(available_at=None, availability_basis='unknown')], T+timedelta(days=3))
    r = observation(availability_basis='assumed')
    with pytest.raises(ValueError): as_of([r], T+timedelta(days=3))
    assert as_of([r], T+timedelta(days=3), allow_assumed=True) == [r]


def test_naive_dates_invented_availability_duplicate_ids_rejected():
    with pytest.raises(ValueError): as_of([], T.replace(tzinfo=None))
    with pytest.raises(ValueError): observation(available_at=T)
    with pytest.raises(ValueError): as_of([observation(), observation()], T)


@pytest.mark.parametrize('hours, expected', [(-1, 0), (0, 0), (12, 1), (24, 1), (25, 0)])
def test_future_label_excludes_past_and_includes_horizon_boundary(hours, expected):
    event = OnsetInterval('fixture', T+timedelta(hours=hours), T+timedelta(hours=hours))
    assert future_event_label(T, timedelta(days=1), [event], coverage_complete=True, currently_below_threshold=True) == expected


def test_label_missingness_and_interval_uncertainty_not_zero():
    assert future_event_label(T, timedelta(days=1), [], coverage_complete=False, currently_below_threshold=True) is None
    assert future_event_label(T, timedelta(days=1), [], coverage_complete=True, currently_below_threshold=False) is None
    uncertain = OnsetInterval('fixture', T+timedelta(hours=23), T+timedelta(hours=25))
    assert future_event_label(T, timedelta(days=1), [uncertain], coverage_complete=True, currently_below_threshold=True) is None
    left = OnsetInterval('fixture', None, T+timedelta(hours=2))
    assert future_event_label(T, timedelta(days=1), [left], coverage_complete=True, currently_below_threshold=True) is None


def test_persistence_alert_is_confirmed_at_second_observation_and_gaps_break_it():
    assert first_persistent_alert([T,T+timedelta(days=1)], [2.,2.], threshold=1., consecutive=2, cadence=timedelta(days=1)) == T+timedelta(days=1)
    assert first_persistent_alert([T,T+timedelta(days=30)], [2.,2.], threshold=1., consecutive=2, cadence=timedelta(days=1)) is None
    assert first_persistent_alert([T,T+timedelta(days=1),T+timedelta(days=3),T+timedelta(days=4)], [0.,2.,2.,2.], threshold=1., consecutive=2, cadence=timedelta(days=1)) == T+timedelta(days=4)


def test_normalization_fits_daily_training_values_and_preserves_zero():
    fit = Normalizer.fit([[0.,10.],[2.,20.],[4.,np.nan]], split='train')
    out, mask = fit.transform([[0.,np.nan],[100.,30.]])
    assert fit.mean.tolist() == [2.,15.]
    assert mask.tolist() == [[True,False],[True,True]]
    assert out[0,0] != 0 and out[0,1] == 0
    assert fit.mean.tolist() == [2.,15.]
    with pytest.raises(ValueError): Normalizer.fit([[1.],[2.]], split='test')
    with pytest.raises(ValueError): Normalizer.fit([[1.],[1.]], split='train')
    with pytest.raises(ValueError): Normalizer.fit([[np.nan],[np.nan]], split='train')


@pytest.mark.parametrize('scores', [[0.,.1,.9,1.],[1.,.9,.1,0.],[.5,.5,.5,.5],[.3,.2,.3,.2]])
def test_ranking_matches_external_reference_including_ties_and_reversal(scores):
    y = [0,0,1,1]; result = ranking_metrics(y, scores)
    assert result['auroc'] == pytest.approx(roc_auc_score(y,scores), abs=1e-14)
    assert result['average_precision'] == pytest.approx(average_precision_score(y,scores), abs=1e-14)


def test_undefined_auc_is_not_chance_and_raw_scores_not_probabilities():
    assert ranking_metrics([0,0], [1.,2.])['auroc'] is None
    assert ranking_metrics([0,0], [1.,2.])['average_precision'] is None
    with pytest.raises(ValueError): probability_metrics([0,1], [-1.,5.], threshold=.5)
    with pytest.raises(ValueError): ranking_metrics([0,1],[np.nan,1.])


@pytest.mark.parametrize('p', [[0.,0.,1.,1.],[1.,1.,0.,0.],[.2,.4,.6,.8],[.5,.5,.5,.5]])
def test_all_probability_metrics_match_factory_independent_oracle(p):
    path = Path(__file__).resolve().parents[2] / 'factory/engine/metrics.py'
    spec = importlib.util.spec_from_file_location('factory_reference_metrics',path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    expected = module.binary_metrics([0,0,1,1],p,.5)
    assert probability_metrics([0,0,1,1],p,threshold=.5) == pytest.approx(expected,abs=1e-12)


def test_holm_and_explicit_cluster_interval():
    assert holm([.01,.04,.03]) == pytest.approx([.03,.06,.06])
    result = paired_cluster_interval([-.2,.1,.3], n_resamples=200, seed=7)
    assert result['n_clusters'] == 3 and result['mean_difference'] == pytest.approx(2/30)
    with pytest.raises(ValueError): paired_cluster_interval([.2], n_resamples=200, seed=7)


def test_calibration_rejects_one_point_and_zero_iqr():
    with pytest.raises(ValueError): RobustCalibration.fit([1.], split='calibration', min_observations=2)
    with pytest.raises(ValueError): RobustCalibration.fit([1.,1.,1.], split='calibration', min_observations=2)
    with pytest.raises(ValueError): RobustCalibration.fit([1.,2.,3.], split='test', min_observations=2)
    cal = RobustCalibration.fit([0.,1.,2.,3.], split='train', min_observations=4)
    assert cal.transform([1.5]).tolist() == [0.]


def test_latent_distance_uses_reference_covariance_not_layernorm_radius():
    ref = LatentReference.fit([[0.,1.],[1.,0.],[-1.,0.],[0.,-1.]], split='train', shrinkage=.2)
    assert ref.squared_distance([[0.,0.],[2.,0.]]).tolist() == pytest.approx([0.,6.])
    assert latent_step_change([[0.,0.],[3.,4.]]).tolist() == [5.]
    with pytest.raises(ValueError): LatentReference.fit([[1.,1.],[1.,1.]], split='train', shrinkage=.2)


def test_finite_input_overflow_cannot_become_a_valid_score_or_reference():
    with pytest.raises(ValueError): RobustCalibration.fit([-1e308,-1e308,1e308,1e308],split='train',min_observations=4)
    cal = RobustCalibration.fit([0.,1e-300,2e-300],split='train',min_observations=3)
    with pytest.raises(ValueError): cal.transform([1e308])
    with pytest.raises(ValueError): LatentReference.fit([[-1e308],[1e308]],split='train',shrinkage=.2)
    ref = LatentReference.fit([[0.],[1.],[-1.]],split='train',shrinkage=.2)
    with pytest.raises(ValueError): ref.squared_distance([[1e308]])
    with pytest.raises(ValueError): latent_step_change([[-1e308],[1e308]])


def test_finite_reconstruction_values_with_overflowing_loss_fail():
    with pytest.raises(ValueError):
        masked_observed_mse(torch.tensor([1e30]),torch.tensor([-1e30]),torch.tensor([True]),torch.tensor([True]))


def test_encoder_prefix_is_independent_of_future_suffix_in_values_and_gradients():
    # FABRICATION-DISCLOSURE: randomized tensor tests a mathematical invariant only.
    torch.manual_seed(4)
    model = CausalHydroEncoder(in_channels=3,d_model=8,tcn_layers=2,transformer_layers=1,n_heads=2,d_ff=16,dropout=0.).double().eval()
    x = torch.randn(2,12,3,dtype=torch.float64,requires_grad=True)
    base = model(x)
    changed = x.detach().clone(); changed[:,7:] += 100
    assert torch.allclose(base[:,:7],model(changed)[:,:7],atol=1e-12,rtol=1e-12)
    gradient = torch.autograd.grad(base[:,6,0].sum(),x)[0]
    assert torch.count_nonzero(gradient[:,7:]) == 0


def test_attention_does_not_conceal_all_masked_nan():
    attn = CausalMultiHeadAttention(8,2,0.)
    with pytest.raises(ValueError): attn(torch.zeros(1,3,8), torch.zeros(1,3,dtype=torch.bool))


def test_masked_loss_excludes_imputed_targets_and_differentiates():
    prediction = torch.tensor([1.,1.,1.],requires_grad=True)
    loss = masked_observed_mse(prediction,torch.tensor([3.,999.,float('nan')]),torch.tensor([True,True,False]),torch.tensor([True,False,False]))
    assert loss.item() == 4.; loss.backward()
    assert prediction.grad.tolist() == [-4.,0.,0.]
    with pytest.raises(ValueError): masked_observed_mse(prediction,prediction,torch.zeros(3,dtype=torch.bool),torch.ones(3,dtype=torch.bool))


def test_reconstruction_targets_are_withheld_from_encoder_input():
    torch.manual_seed(9)
    model = MaskedHydroModel(2,d_model=8,tcn_layers=1,transformer_layers=1,n_heads=2,d_ff=16,dropout=0.).eval()
    x = torch.tensor([[[10.,20.],[30.,40.]]]); observed = torch.ones_like(x,dtype=torch.bool)
    seen = []
    hook = model.encoder.register_forward_pre_hook(lambda module,args: seen.append(args[0].clone()))
    scores = leave_channel_out_score(model,x,observed); hook.remove()
    assert torch.isfinite(scores).all()
    assert seen[0][...,0].tolist() == [[0.,0.]] and seen[0][...,2].tolist() == [[0.,0.]]
    assert seen[1][...,1].tolist() == [[0.,0.]] and seen[1][...,3].tolist() == [[0.,0.]]


def test_ealstm_dtype_and_dimensions():
    model = EALSTMModel(dynamic_dim=2,static_dim=3,hidden_dim=4).double().eval()
    assert model(torch.zeros(2,4,2,dtype=torch.float64),torch.zeros(2,3,dtype=torch.float64)).shape == (2,)
    with pytest.raises(ValueError): model(torch.zeros(2,4,2,dtype=torch.float64),torch.zeros(2,2,dtype=torch.float64))


def test_persistence_is_distinct_from_change_and_cusum_state_is_continuous():
    assert persistence_forecast(4.,3).tolist() == [4.,4.,4.]
    assert rate_of_change([1.,3.,4.]).tolist() == [2.,1.]
    kw = dict(calibration_mean=0.,calibration_scale=1.,alpha=.5,slack=.2)
    whole, state = ewma_cusum([1.,2.,3.,4.],initial_ewma=0.,initial_cusum=0.,**kw)
    left, partial = ewma_cusum([1.,2.],initial_ewma=0.,initial_cusum=0.,**kw)
    right, final = ewma_cusum([3.,4.],initial_ewma=partial['ewma'],initial_cusum=partial['cusum'],**kw)
    assert np.array_equal(whole,np.concatenate([left,right])) and state == final
