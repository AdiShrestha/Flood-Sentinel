"""FABRICATION-DISCLOSURE: constructed engineering cases, never observations."""
from dataclasses import replace
from datetime import datetime,timedelta,timezone
import hashlib,json,itertools
import numpy as np
import pytest
from flood_sentinel.evidence import (HydroRow,decode_continuous,calendar,label_issue,
    labels_from_rows,derive_onsets,fit_unique_normalizer,network_components)
from flood_sentinel.temporal import OnsetInterval
from flood_sentinel.continuous import ContinuousBaselines
from flood_sentinel.adapters.availability import AvailabilityAdapter,CausalLeakageError
from flood_sentinel.adapters.exposure import ExposureAdapter

T=datetime(2000,1,1,tzinfo=timezone.utc)


def row(i,value):
    return HydroRow(str(i),'fixture-'+str(i),'0'*64,i,'fixture-site','fixture-series',
        T+timedelta(hours=i),None if value is None else str(value),'m3/s',value,'Approved',(),
        None,value is not None,value is not None,None if value is not None else 'missing')


def test_interval_labels_against_enumerated_support():
    # Distinct oracle: enumerate every compatible integer-minute onset in (L,U]
    # rather than copying containment inequalities from the implementation.
    for lo,hi in itertools.combinations_with_replacement(range(-3,7),2):
        support=[lo] if lo==hi else list(range(lo+1,hi+1))
        outcomes={int(0<t<=3) for t in support}
        expected=next(iter(outcomes)) if len(outcomes)==1 else None
        ev=OnsetInterval('fixture',T+timedelta(minutes=lo),T+timedelta(minutes=hi))
        actual=label_issue(T,timedelta(minutes=3),[ev],current_below=True,coverage_complete=True).label
        # Integer support misses infinitesimal overlap at a boundary for a
        # continuous interval; add half-minute points through a second grid.
        if lo!=hi:
            points=[lo+k/2 for k in range(1,2*(hi-lo)+1)]
            values={int(0<t<=3) for t in points}
            expected=next(iter(values)) if len(values)==1 else None
        assert actual==expected,(lo,hi,expected,actual)


def test_truth_coverage_and_ongoing_are_not_default_negatives():
    assert label_issue(T,timedelta(hours=1),[],current_below=True,coverage_complete=False).label is None
    assert label_issue(T,timedelta(hours=1),[],current_below=None,coverage_complete=True).label is None
    assert label_issue(T,timedelta(hours=1),[],current_below=True,coverage_complete=True,ongoing=True).label is None
    assert ExposureAdapter.compute_sample_exposure('f_20000101T000000Z','f',T,[]).has_flood_event is None
    e=[OnsetInterval('f',T-timedelta(hours=1),T+timedelta(hours=1))]
    assert label_issue(T,timedelta(hours=2),e,current_below=True,coverage_complete=True).label is None
    e=[OnsetInterval('f',T,T+timedelta(hours=1))]
    assert label_issue(T,timedelta(hours=2),e,current_below=True,coverage_complete=False).label==1
    outside=[dict(site_no='fixture',event_id='fixture-event',
        onset_lower_utc=(T+timedelta(days=2)).isoformat(),
        onset_upper_utc=(T+timedelta(days=3)).isoformat())]
    x=ExposureAdapter.compute_sample_exposure('fixture_20000101T000000Z','fixture',T,outside,
        coverage_complete=True,currently_below_threshold=True,ongoing=False)
    assert x.has_flood_event is False and x.lead_time_upper_hours == 72


def test_source_to_label_mutation_missing_zero_and_censoring():
    rows=[row(i,float(v)) for i,v in enumerate([1,1,3,1,1])]
    get=lambda rs: labels_from_rows(rs,[T+timedelta(hours=1)],2.,cadence=timedelta(hours=1),horizon=timedelta(hours=2))[0][0][1]
    assert get(rows).label==1
    changed=[replace(r,value_si=1.) if r.row_index==2 else r for r in rows]
    assert get(changed).label==0
    missing=[replace(r,value_original=None,value_si=None,usable_truth=False,
                     usable_input_quality=False,exclusion='missing_value') if r.row_index==2 else r for r in changed]
    assert get(missing).label is None
    zero=[replace(r,value_si=0.) if r.row_index==2 else r for r in changed]
    assert get(zero).label==0
    onsets,_=derive_onsets([row(0,3.),row(1,4.)],2.,cadence=timedelta(hours=1))
    assert onsets[0].lower is None
    # Missing below-threshold intervals cannot rearm a second episode.
    rs=[row(0,3.),row(1,1.),row(74,1.),row(75,3.)]
    onsets,risk=derive_onsets(rs,2.,cadence=timedelta(hours=1))
    assert len(onsets)==1 and risk[T+timedelta(hours=74)] is False


def test_actual_release_checks_and_timezone():
    r=dict(record_id='fixture',observation_start_utc=T.isoformat(),observation_end_utc=T.isoformat(),
           available_utc=T.isoformat(),availability_basis='observed')
    check=lambda x,**k: AvailabilityAdapter.audit_sample_causality('f',T,[x],**k)
    assert check(r).is_causally_valid
    for key in ['available_utc','availability_basis','observation_end_utc']:
        bad=r.copy();bad.pop(key)
        with pytest.raises((ValueError,CausalLeakageError)):check(bad)
    with pytest.raises(CausalLeakageError):check(dict(r,available_utc=(T+timedelta(hours=1)).isoformat()))
    with pytest.raises(CausalLeakageError):check(dict(r,availability_basis='assumed'))
    assert check(dict(r,availability_basis='assumed'),allow_assumed=True).is_causally_valid
    with pytest.raises(ValueError):check(dict(r,observation_end_utc='2000-01-01T00:00:00'))
    # A revised value has its own captured release; an earlier value timestamp
    # cannot grant it earlier access.
    with pytest.raises(CausalLeakageError):check(dict(r,available_utc=(T+timedelta(days=1)).isoformat()))


def test_unique_fit_window_duplication_and_membership():
    rows=[row(i,float(i)) for i in range(4)];allowed={r.record_id for r in rows}
    a,ids=fit_unique_normalizer(rows,allowed);b,ids2=fit_unique_normalizer(rows+rows[:2],allowed)
    assert ids==ids2 and a.mean==b.mean and a.count==b.count and a.scale==b.scale
    with pytest.raises(ValueError):fit_unique_normalizer(rows,allowed-{'3'})
    with pytest.raises(ValueError):fit_unique_normalizer(rows+[replace(rows[0],value_si=50.)],allowed)


def test_networks_need_physical_evidence():
    with pytest.raises(ValueError):network_components(['upper','lower'],[],topology_verified=False)
    for names in [('upper','lower'),('independent-A','independent-B')]:
        groups=network_components(names,[names],topology_verified=True)
        assert len(set(groups.values()))==1


def test_continuous_persistence_and_spc_hand_calculation():
    b=ContinuousBaselines(0.,1.,1.,0.,.5,timedelta(hours=1))
    assert b.update(T,None,cadence=timedelta(hours=1))==dict(persistence=None,spc=None,observation_age_seconds=None)
    x=b.update(T+timedelta(hours=1),2.,cadence=timedelta(hours=1))
    assert x['persistence']==2. and x['spc']==2. # z=2,C=2 -> .5*(2+2)
    x=b.update(T+timedelta(hours=2),2.,cadence=timedelta(hours=1))
    assert x['spc']==2.5 # z=2,C=.5*2+2=3
    assert b.update(T+timedelta(hours=3),None,cadence=timedelta(hours=1))['persistence']==2.
    assert b.update(T+timedelta(hours=4),None,cadence=timedelta(hours=1))['persistence'] is None
    with pytest.raises(ValueError):b.update(T+timedelta(hours=6),1.,cadence=timedelta(hours=1))


def test_calendar_retains_unobserved_times():
    assert calendar(T,T+timedelta(days=3),timedelta(days=1))==[T+timedelta(days=i) for i in range(3)]


def test_raw_decode_mutations_reach_labels_and_preserve_nulls():
    # FABRICATION-DISCLOSURE: schema-shaped constructed records; no provider
    # acquisition, published observation, or research row is created here.
    def payload(values):
        return json.dumps(dict(type='FeatureCollection',numberReturned=len(values),features=[
            dict(id='fixture-version-'+str(i),properties=dict(time_series_id='fixture-series',
                monitoring_location_id='fixture-site',parameter_code='00060',statistic_id='00011',
                time=(T+timedelta(hours=i)).isoformat(),value=None if v is None else str(v),
                unit_of_measure='ft^3/s',approval_status='Approved',qualifier=None,last_modified=None))
            for i,v in enumerate(values)])).encode()
    def decode(raw):
        return decode_continuous(raw,hashlib.sha256(raw).hexdigest(),site='fixture-site',series='fixture-series')
    def label(values):
        rows=decode(payload(values))
        return labels_from_rows(rows,[T+timedelta(hours=1)],2.*.028316846592,
            cadence=timedelta(hours=1),horizon=timedelta(hours=2))[0][0][1].label
    assert label([1,1,3,1])==1 and label([1,1,1,1])==0
    assert label([1,1,None,1]) is None
    raw=payload([0,None]);rows=decode(raw)
    assert rows[0].value_si==0. and rows[0].usable_truth
    assert rows[1].value_si is None and not rows[1].usable_truth
    assert all(r.available_at is None and r.availability_basis=='unknown' for r in rows)
    with pytest.raises(ValueError,match='hash'):decode_continuous(raw,'0'*64,site='fixture-site',series='fixture-series')
    wrong=raw.replace(b'00060',b'00065')
    with pytest.raises(ValueError,match='identity'):decode(wrong)
    # A new source version at an existing time needs explicit resolution.
    from flood_sentinel.evidence import unique_rows
    with pytest.raises(ValueError,match='versions'):
        unique_rows([rows[0],replace(rows[0],record_id='different-raw-version',provider_id='new-version')])
