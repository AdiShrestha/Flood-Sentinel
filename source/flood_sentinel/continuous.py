"""Chronological baseline state; missing inputs cannot initialize observations."""
from dataclasses import dataclass
from datetime import datetime, timedelta
import math
from .temporal import utc


@dataclass
class ContinuousBaselines:
    mean: float
    scale: float
    alpha: float
    slack: float
    leak: float
    max_age: timedelta
    time: datetime | None = None
    last_observed_at: datetime | None = None
    last_value: float | None = None
    ewma: float | None = None
    cusum: float = 0.

    def __post_init__(self):
        if (not all(type(x) in (float,int) and math.isfinite(x) for x in
                    [self.mean,self.scale,self.alpha,self.slack,self.leak])
            or self.scale<=0 or not 0<self.alpha<=1 or not 0<self.leak<=1 or self.slack<0
            or self.max_age<=timedelta(0)):
            raise ValueError('Supported finite SPC parameters required')

    def update(self, time: datetime, value: float | None, *, cadence: timedelta):
        time=utc(time)
        if cadence<=timedelta(0): raise ValueError('Positive cadence required')
        if self.time is not None and time-self.time!=cadence:
            raise ValueError('Update every chronological issue, including missing issues')
        if value is not None and (type(value) not in (float,int) or not math.isfinite(value)):
            raise ValueError('Finite observation or explicit None required')
        self.time=time
        if self.ewma is None: self.ewma=self.mean
        if value is not None:
            self.last_value=float(value);self.last_observed_at=time
            self.ewma=self.alpha*value+(1-self.alpha)*self.ewma
        else:
            self.ewma=.15*self.mean+.85*self.ewma
        z=(self.ewma-self.mean)/(self.scale*math.sqrt(self.alpha/(2-self.alpha)))
        self.cusum=max(0.,self.leak*self.cusum+z-self.slack) if value is not None else self.leak*self.cusum
        if not all(math.isfinite(v) for v in [self.ewma,self.cusum,z]):
            raise ValueError('SPC overflow')
        persistence=None if self.last_observed_at is None or time-self.last_observed_at>self.max_age else self.last_value
        # An internal mean/prior state is never presented as an observation.
        score=None if value is None else .5*z+.5*self.cusum
        return dict(persistence=persistence,spc=score,observation_age_seconds=
            None if self.last_observed_at is None else (time-self.last_observed_at).total_seconds())
