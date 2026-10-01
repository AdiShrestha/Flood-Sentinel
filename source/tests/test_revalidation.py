"""Adversarial engineering fixtures, never observational hydrology evidence.

# FABRICATION-DISCLOSURE: every value, record and tensor in this module is
# constructed to test a stated arithmetic or information-flow property.
"""
from dataclasses import replace
from datetime import timedelta
import math
import numpy as np
import pytest
import torch
from flood_sentinel.metrics import probability_metrics, paired_cluster_interval
from flood_sentinel.preprocessing import Normalizer
from flood_sentinel.scoring import LatentReference, RobustCalibration
from flood_sentinel.baselines import rate_of_change, ewma_cusum
from flood_sentinel.model import CausalHydroEncoder
from flood_sentinel.reconstruction import MaskedHydroModel
from flood_sentinel.ea_lstm import EALSTMCell, EALSTMModel
from flood_sentinel.temporal import as_of, OnsetInterval, future_event_label
from test_engine import observation, T


def test_exact_and_declared_clipped_log_losses_have_distinct_boundary_semantics():
    assert probability_metrics([0,1],[0.,1.],threshold=.5)['log_loss'] == 0.
    assert math.isinf(probability_metrics([0,1],[1.,0.],threshold=.5)['log_loss'])
    assert probability_metrics([0,1],[.2,.7],threshold=.5)['log_loss'] == pytest.approx(-math.log(.8*.7)/2)
    assert probability_metrics([0,1],[1.,0.],threshold=.5,log_epsilon=1e-15)['log_loss'] == pytest.approx(-math.log(1e-15))
    for epsilon in (True,0.,.5,'0.01'):
        with pytest.raises(ValueError): probability_metrics([0,1],[.2,.7],threshold=.5,log_epsilon=epsilon)


@pytest.mark.parametrize('bad', [['1','2'],[1+2j,2+3j],[True,False]])
def test_numeric_input_is_not_silently_coerced(bad):
    with pytest.raises(ValueError): rate_of_change(bad)
    with pytest.raises(ValueError): Normalizer.fit(np.asarray(bad).reshape(-1,1),split='train')
    with pytest.raises(ValueError): probability_metrics([0,1],bad,threshold=.5)


def test_fitted_arrays_are_copied_and_cannot_be_mutated_or_made_writeable():
    mu=np.array([1.]); scale=np.array([2.]); med=np.array([1.]); counts=np.array([2])
    fitted=Normalizer(mu,scale,med,counts); mu[0]=100
    assert fitted.mean[0]==1.
    for array in (fitted.mean,fitted.scale,fitted.median,fitted.count):
        with pytest.raises(ValueError): array[0]=123
        with pytest.raises(ValueError): array.setflags(write=True)
    ref=LatentReference.fit([[-1.,0.],[1.,0.],[0.,1.]],split='train',shrinkage=.2)
    with pytest.raises(ValueError): ref.cholesky[0,0]=100
    with pytest.raises(ValueError): Normalizer([0.],[0.],[0.],np.array([2]))
    with pytest.raises(ValueError): RobustCalibration(0.,1.,0)
    with pytest.raises(ValueError): LatentReference([0.],[[0.]],.2,2)


def test_baseline_hand_oracle_and_overflow_are_explicit():
    assert rate_of_change([1.,4.,10.],step_duration=3.).tolist()==[1.,2.]
    kw=dict(calibration_mean=0.,calibration_scale=2.,alpha=.5,slack=.25,initial_ewma=0.,initial_cusum=0.)
    scores,state=ewma_cusum([2.,4.],**kw)
    assert scores.tolist()==[.25,1.25] and state=={'ewma':2.5,'cusum':1.25}
    with pytest.raises(ValueError): rate_of_change([-1e308,1e308])
    with pytest.raises(ValueError): ewma_cusum([1e308],**{**kw,'calibration_mean':-1e308,'alpha':1.})
    with pytest.raises(ValueError): paired_cluster_interval([1e308,1e308],n_resamples=100,seed=1)
    with pytest.raises(ValueError): paired_cluster_interval([0.,1.],n_resamples=100,seed=True)


def test_string_false_cannot_allow_assumed_source_availability():
    with pytest.raises(ValueError): as_of([observation(availability_basis='assumed')],T,allow_assumed='false')
    with pytest.raises(ValueError): observation(value='12')


@pytest.mark.parametrize('params', [{'d_model':1,'n_heads':1},{'dropout':1.},{'d_ff':0},{'n_heads':True}])
def test_degenerate_encoder_configuration_is_rejected(params):
    with pytest.raises(ValueError): CausalHydroEncoder(tcn_layers=0,transformer_layers=0,**params)


def test_empty_batch_and_nonfinite_weights_cannot_produce_admissible_neural_outputs():
    model=CausalHydroEncoder(in_channels=1,d_model=2,n_heads=1,tcn_layers=0,transformer_layers=0).eval()
    with pytest.raises(ValueError): model(torch.empty(0,2,1))
    with torch.no_grad(): model.input_proj.weight.fill_(float('inf'))
    with pytest.raises(ValueError): model(torch.ones(1,2,1))
    with pytest.raises(ValueError): EALSTMModel(dynamic_dim=0)
    with pytest.raises(ValueError): EALSTMModel()(torch.empty(0,2,6),torch.empty(0,8))


def test_bound_training_objective_withholds_hidden_values_from_predictions_and_input_gradients():
    torch.manual_seed(61)
    model=MaskedHydroModel(2,d_model=8,n_heads=2,tcn_layers=1,transformer_layers=1,d_ff=8,dropout=0.).double().eval()
    values=torch.tensor([[[2.,3.],[4.,5.]]],dtype=torch.float64,requires_grad=True)
    observed=torch.ones_like(values,dtype=torch.bool); hidden=torch.zeros_like(observed); hidden[...,0]=True
    predictions=[]
    hook=model.head.register_forward_hook(lambda m,args,out:predictions.append(out.detach().clone()))
    first=model.masked_loss(values,observed,hidden)
    changed=values.detach().clone(); changed[hidden]+=100
    second=model.masked_loss(changed,observed,hidden); hook.remove()
    assert torch.equal(predictions[0],predictions[1]) and first.item()!=second.item()
    gradient=torch.autograd.grad(first,values)[0]
    assert torch.count_nonzero(gradient[hidden])==0
    observed[...,0]=False
    with pytest.raises(ValueError): model.masked_loss(values,observed,hidden)


def test_ealstm_recurrence_matches_independent_scalar_equations():
    cell=EALSTMCell(1,1,1).double()
    with torch.no_grad():
        for layer in (cell.w_i,cell.w_f,cell.w_c,cell.w_o): layer.weight.fill_(.3); layer.bias.fill_(.1)
        for layer in (cell.u_f,cell.u_c,cell.u_o): layer.weight.fill_(.2)
    sigmoid=lambda x:1/(1+math.exp(-x))
    gate=sigmoid(.3*2.+.1); h=c=0.
    ht=ct=torch.zeros(1,1,dtype=torch.float64)
    for x in (1.,-2.):
        drive=.3*x+.1+.2*h
        c=sigmoid(drive)*c+gate*math.tanh(drive); h=sigmoid(drive)*math.tanh(c)
        ht,ct=cell(torch.tensor([[x]],dtype=torch.float64),ht,ct,torch.tensor([[gate]],dtype=torch.float64))
        assert ht.item()==pytest.approx(h,abs=1e-14) and ct.item()==pytest.approx(c,abs=1e-14)


def test_interval_label_matches_all_compatible_onsets_across_issue_and_horizon_boundaries():
    # Enumerate intervals spanning each boundary; classify their entire support,
    # rather than substituting an interval midpoint for an observed onset.
    for low in range(-2,7):
        for high in range(low,7):
            onset=OnsetInterval('fixture',T+timedelta(hours=low),T+timedelta(hours=high))
            possibilities=[high] if low==high else [v/2 for v in range(2*low+1,2*high+1)]
            truth=[0 < value <= 4 for value in possibilities]
            expected=1 if all(truth) else 0 if not any(truth) else None
            assert future_event_label(T,timedelta(hours=4),[onset],coverage_complete=True,currently_below_threshold=True)==expected


def test_forensic_comparison_rejects_equal_length_dates_in_different_order():
    import importlib.util
    from pathlib import Path
    import pandas as pd
    path=Path(__file__).resolve().parents[2]/'project/audit/tools/inspect_legacy_evidence.py'
    spec=importlib.util.spec_from_file_location('forensic_check',path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    left=pd.DataFrame({'date':['2020-01-01','2020-01-02']})
    module.require_same_dates(left,left.copy())
    with pytest.raises(ValueError): module.require_same_dates(left,left.iloc[::-1])
    with pytest.raises(ValueError): module.require_same_dates(left,pd.DataFrame({'date':['2020-01-01','2020-01-01']}))
