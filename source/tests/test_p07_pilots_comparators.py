"""Retired scientific pilot assumptions must fail closed.

FABRICATION-DISCLOSURE: all tensors below are constructed software fixtures.
No training on the quarantined historical cohort is an acceptance check.
"""
from types import SimpleNamespace
from datetime import datetime,timedelta,timezone
import numpy as np
import pytest
import torch
from flood_sentinel.pilots import EALSTMPilotTrainer,EWMACUSUMComparator,PersistenceComparator
from flood_sentinel.continuous import ContinuousBaselines
from flood_sentinel.dataset import CausalHydroDataset


def test_persistence_unavailable_until_observed():
    s=SimpleNamespace(values=torch.tensor([[0.],[3.],[0.]]),
                      observed=torch.tensor([[False],[True],[False]]))
    assert PersistenceComparator.evaluate_sample(s)==3.
    s.observed[:]=False
    assert PersistenceComparator.evaluate_sample(s) is None


def test_window_reset_and_invented_scale_are_rejected():
    with pytest.raises(ValueError):EWMACUSUMComparator(calibration_scale=0.)
    with pytest.raises(ValueError,match="Window-reset"):
        EWMACUSUMComparator().evaluate_sample(None)
    d=SimpleNamespace(get_raw_observations_matrix=lambda:np.ones((4,1)))
    with pytest.raises(ValueError,match="Constant"):
        EWMACUSUMComparator.fit_from_dataset(d)


def test_station_id_does_not_supply_catchment_attributes():
    trainer=EALSTMPilotTrainer(hidden_dim=8)
    with pytest.raises(ValueError,match="Station-ID"):
        trainer._get_static_features(["fixture-site"])


def test_unique_raw_matrix_is_invariant_to_duplicated_windows(tmp_path):
    """Constructed CSV fixtures exercise the verified public loader, including zero."""
    import csv
    import hashlib
    site = "fixture-A"
    times = ["2000-01-01T11:30:00Z", "2000-01-01T11:45:00Z", "2000-01-01T12:00:00Z"]
    records = [dict(record_id=str(i), site_no=site, parameter="discharge_cms",
        series_id="fixture-q", provider_record_id="fixture-version-"+str(i),
        provider="constructed-fixture", origin="observational", unit_si="m3/s",
        timestamp_utc=ts, observation_start_utc=ts, observation_end_utc=ts,
        availability_basis="observed", available_utc=ts, value_si=str(value),
        raw_sha256=hashlib.sha256(("constructed software fixture "+str(i)).encode()).hexdigest())
        for i,(ts,value) in enumerate(zip(times,[0.,2.,4.]))]
    # The observational schema is exercised only inside disclosed temporary
    # software fixtures; these rows never enter provider/study evidence.
    issues = [("20000101T120000Z","0|1"),("20000101T121500Z","1|2"),
              ("20000101T123000Z","0|1|2")]
    def load(name, count):
        directory=tmp_path/name;directory.mkdir()
        source=directory/"sources.csv";cohort=directory/"cohort.csv"
        with source.open("w",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
        rows=[dict(sample_id=site+"_"+stamp,label="0",group_id="fixture-group",split="train",source_ids=ids)
              for stamp,ids in issues[:count]]
        with cohort.open("w",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        return CausalHydroDataset(cohort,source,split="train",channels=("discharge_cms",),
            lookback_hours=1,series_by_site={site:{"discharge_cms":"fixture-q"}})
    first,overlapping=load("two_windows",2),load("three_windows",3)
    a,b=first.get_raw_observations_matrix(),overlapping.get_raw_observations_matrix()
    np.testing.assert_array_equal(a,b)
    np.testing.assert_array_equal(b[:,0],[0.,2.,4.])
    assert first.raw_fit_record_ids==overlapping.raw_fit_record_ids==("0","1","2")


def test_continuous_state_survives_chunk_boundaries():
    t=datetime(2000,1,1,tzinfo=timezone.utc);step=timedelta(hours=1)
    one=ContinuousBaselines(0.,1.,.5,.5,.9,step)
    two=ContinuousBaselines(0.,1.,.5,.5,.9,step)
    values=[1.,2.,None,3.]
    a=[one.update(t+i*step,v,cadence=step) for i,v in enumerate(values)]
    b=[]
    for indices in [range(2),range(2,4)]:
        b.extend(two.update(t+i*step,values[i],cadence=step) for i in indices)
    assert a==b
