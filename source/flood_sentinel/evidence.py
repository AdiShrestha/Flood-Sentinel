"""Development source-to-label contract v1. No learner or model imports.

Sampled high-flow crossings are distinct from inundation or official flood truth.
Final historical values carry unknown historical availability unless separately
captured. A complete nominal grid establishes only the declared sampled target.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
import math
from typing import Sequence
from .temporal import OnsetInterval, future_event_label, utc
from .identifiers import require_identifier
from .validation import real_scalar


def strict_json(raw: bytes):
    def pairs(items):
        out = {}
        for k,v in items:
            if k in out:
                raise ValueError('Duplicate JSON key: '+k)
            out[k] = v
        return out
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def instant(text):
    return utc(datetime.fromisoformat(text))


@dataclass(frozen=True)
class HydroRow:
    record_id: str
    provider_id: str
    raw_sha256: str
    row_index: int
    site: str
    series: str
    time: datetime
    value_original: str | None
    unit_original: str
    value_si: float | None
    approval: str | None
    qualifiers: tuple[str, ...]
    last_modified_original: str | None
    usable_truth: bool
    usable_input_quality: bool
    exclusion: str | None
    # Explicitly no inferred historical publication from time or last_modified.
    available_at: datetime | None = None
    availability_basis: str = 'unknown'
    provider: str = 'USGS-OGC-v1'
    origin: str = 'observational'

    def __post_init__(self):
        for field in ('record_id', 'provider_id', 'site', 'series'):
            require_identifier(getattr(self, field), field=field)
        if type(self.row_index) is not int or self.row_index < 0:
            raise ValueError('row_index must be a nonnegative integer')
        if not isinstance(self.raw_sha256, str) or len(self.raw_sha256) != 64 or any(
            c not in '0123456789abcdef' for c in self.raw_sha256
        ):
            raise ValueError('raw_sha256 must be lowercase SHA-256 hex')
        require_identifier(self.unit_original, field='unit_original')
        utc(self.time)
        if self.value_original is not None and not isinstance(self.value_original, str):
            raise ValueError('value_original must retain provider text or null')
        if self.value_si is not None:
            if real_scalar(self.value_si) < 0:
                raise ValueError('Discharge value must be nonnegative')
        elif self.usable_truth or self.usable_input_quality:
            raise ValueError('Missing value cannot be marked usable')
        if type(self.usable_truth) is not bool or type(self.usable_input_quality) is not bool:
            raise ValueError('Usability flags must be booleans')
        if not isinstance(self.qualifiers, tuple) or any(not isinstance(x, str) for x in self.qualifiers):
            raise ValueError('qualifiers must be a tuple of source strings')


def decode_continuous(raw: bytes, expected_sha: str, *, site: str, series: str) -> list[HydroRow]:
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha:
        raise ValueError('Raw hash mismatch')
    data = strict_json(raw)
    if data.get('type') != 'FeatureCollection' or data.get('numberReturned') != len(data['features']):
        raise ValueError('Feature collection/cardinality mismatch')
    out = []
    for i,f in enumerate(data['features']):
        p = f['properties']
        if (p['monitoring_location_id'] != site or p['time_series_id'] != series
            or p['parameter_code'] != '00060' or p.get('statistic_id') != '00011'):
            raise ValueError('Source identity/statistic mismatch')
        if not isinstance(f['id'], str) or not f['id']:
            raise ValueError('Provider version ID missing')
        if p['unit_of_measure'] != 'ft^3/s':
            raise ValueError('Unverified discharge units')
        text = p['value']
        if text is not None and not isinstance(text, str):
            raise ValueError('Provider numeric strings/null required')
        v = None if text is None else float(text)
        if v is not None and (not math.isfinite(v) or v < 0):
            raise ValueError('Invalid discharge/sentinel needs explicit decode')
        q = p.get('qualifier')
        if q is None: qualifiers = ()
        elif isinstance(q,str): qualifiers = (q,)
        elif isinstance(q,list) and all(isinstance(x,str) for x in q): qualifiers = tuple(q)
        else: raise ValueError('Malformed qualifier')
        approval = p.get('approval_status')
        # Until code-specific semantics have authoritative evidence, qualify only
        # Approved/Provisional unflagged measurements. Never infer flags usable.
        exclusion = ('missing_value' if v is None else
                     'unknown_approval' if approval not in {'Approved','Provisional'} else
                     'qualifier_requires_review' if qualifiers else None)
        out.append(HydroRow(digest+':'+str(i), f['id'], digest, i, site, series,
            instant(p['time']), text, p['unit_of_measure'],
            None if v is None else v * 0.028316846592, approval, qualifiers,
            p.get('last_modified'), exclusion is None, exclusion is None, exclusion))
    if len({r.provider_id for r in out}) != len(out):
        raise ValueError('Duplicate provider version ID')
    return out


def unique_rows(rows: Sequence[HydroRow]) -> list[HydroRow]:
    out = {}; versions = {}
    for r in rows:
        if r.record_id in out and out[r.record_id] != r:
            raise ValueError('Conflicting raw record ID')
        key = (r.site,r.series,r.time)
        if key in versions and versions[key] != r.record_id:
            raise ValueError('Multiple versions of one observation require explicit vintage resolution')
        versions[key] = r.record_id
        out[r.record_id] = r
    return sorted(out.values(),key=lambda r:(r.time,r.record_id))


def calendar(start: datetime, end: datetime, cadence: timedelta) -> list[datetime]:
    start,end = utc(start),utc(end)
    if start >= end or not isinstance(cadence,timedelta) or cadence <= timedelta(0):
        raise ValueError('Nonempty half-open calendar and positive cadence required')
    out = []; t = start
    while t < end:
        out.append(t); t += cadence
    return out


def reference_quantile(rows: Sequence[HydroRow], allowed_ids: set[str], p: float = .99) -> float:
    import numpy as np
    allowed_ids = {require_identifier(x, field='allowed reference record_id') for x in allowed_ids}
    rows = unique_rows(rows)
    if any(r.record_id not in allowed_ids for r in rows):
        raise ValueError('Prohibited reference record')
    values = [r.value_si for r in rows if r.usable_truth]
    if len(values) < 2 or not 0 < p < 1:
        raise ValueError('Insufficient reference support')
    return float(np.quantile(values,p,method='median_unbiased'))


def derive_onsets(rows: Sequence[HydroRow], threshold: float, *, cadence: timedelta):
    """Keep interval bounds across gaps; 72 observed below hours rearm episodes.

    Missing intervals never establish recession. A first above observation is
    left-censored. `at_risk` is evaluator state, never a learner feature.
    """
    if not math.isfinite(threshold) or threshold < 0 or cadence <= timedelta(0):
        raise ValueError('Invalid threshold/cadence')
    rows = unique_rows(rows)
    if len({(r.site,r.series) for r in rows}) > 1:
        raise ValueError('One site/series per episode stream required')
    onsets=[]; at_risk={}; last_below=None; below_start=None; previous=None; active=False
    for r in rows:
        if previous is not None and r.time-previous != cadence:
            below_start=None
        previous=r.time
        if not r.usable_truth:
            below_start=None; at_risk[r.time]=None; continue
        if r.value_si <= threshold:
            if below_start is None: below_start=r.time
            if active and r.time-below_start >= timedelta(hours=72): active=False
            last_below=r.time
        else:
            if not active:
                onsets.append(OnsetInterval(r.record_id,last_below,r.time))
            active=True; below_start=None
        at_risk[r.time] = not active and r.value_si <= threshold
    return onsets,at_risk


@dataclass(frozen=True)
class LabelEvidence:
    label: int | None
    status: str
    reason: str
    coverage_complete: bool
    evidence_ids: tuple[str,...]


def label_issue(issue, horizon, onsets, *, current_below: bool | None,
                coverage_complete: bool, evidence_ids=(), ongoing: bool | None = False):
    evidence_ids=tuple(require_identifier(x, field='evidence record_id') for x in evidence_ids)
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError('Duplicate evidence record IDs')
    if current_below is not None and type(current_below) is not bool:
        raise ValueError('Explicit current state required')
    if type(coverage_complete) is not bool or (ongoing is not None and type(ongoing) is not bool):
        raise ValueError('Explicit coverage/ongoing state required')
    if current_below is not True or ongoing is not False:
        return LabelEvidence(None,'unknown','current_state_unknown_or_ongoing',coverage_complete,tuple(evidence_ids))
    value=future_event_label(issue,horizon,onsets,coverage_complete=coverage_complete,
                             currently_below_threshold=True)
    if value is None:
        # A complete horizon can still have an interval straddling a boundary.
        reason='onset_boundary_ambiguous' if future_event_label(issue,horizon,onsets,
            coverage_complete=True,currently_below_threshold=True) is None else 'incomplete_future_monitoring'
        return LabelEvidence(None,'unknown',reason,coverage_complete,tuple(evidence_ids))
    return LabelEvidence(value,'positive' if value else 'negative',
        'definite_future_onset' if value else 'complete_sampled_future_monitoring',coverage_complete,tuple(evidence_ids))


def labels_from_rows(rows, issues, threshold, *, cadence=timedelta(minutes=15), horizon=timedelta(days=1)):
    rows=unique_rows(rows); index={r.time:r for r in rows}
    onsets,risk=derive_onsets(rows,threshold,cadence=cadence)
    out=[]
    for issue in issues:
        required=calendar(issue,issue+horizon+cadence,cadence)
        selected=[index[t] for t in required if t in index]
        complete=len(selected)==len(required) and all(r.usable_truth for r in selected)
        current=index.get(issue)
        below=None if current is None or not current.usable_truth else current.value_si<=threshold
        # Absence of a catalog entry is never sufficient negative evidence.
        label=label_issue(issue,horizon,onsets,current_below=below,coverage_complete=complete,
                          ongoing=None if risk.get(issue) is None else not risk[issue],
                          evidence_ids=[r.record_id for r in selected])
        out.append((issue,label))
    return out,onsets


def fit_unique_normalizer(rows, allowed_ids):
    """Uniform weight per unique permitted raw record, one discharge channel."""
    import numpy as np
    from .preprocessing import Normalizer
    allowed_ids={require_identifier(x, field='allowed training record_id') for x in allowed_ids}
    rows=unique_rows(rows)
    if any(r.record_id not in allowed_ids for r in rows): raise ValueError('Prohibited fit record')
    x=np.array([[r.value_si if r.usable_input_quality else np.nan] for r in rows])
    return Normalizer.fit(x,split='train'),tuple(r.record_id for r in rows)


def network_components(sites, edges, *, topology_verified: bool):
    """Use physical edges; refuse an independence claim without topology evidence."""
    if topology_verified is not True: raise ValueError('Physical topology remains unknown')
    parent={s:s for s in sites}
    def find(x):
        while parent[x]!=x: x=parent[x]
        return x
    for a,b in edges:
        if a not in parent or b not in parent: raise ValueError('Unknown topology site')
        parent[find(a)]=find(b)
    return {s:find(s) for s in parent}
