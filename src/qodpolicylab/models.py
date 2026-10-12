"""Strict versioned configuration and immutable, causal policy observations."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from math import isfinite


def number(value, label, lower=0., upper=None, inclusive=True):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not isfinite(value):
        raise ValueError(f'{label} must be finite numeric')
    if value < lower or (not inclusive and value == lower) or (upper is not None and value > upper):
        raise ValueError(f'{label} outside allowed range')
    return float(value)


@dataclass(frozen=True)
class Observation:
    t_s: float
    latency_ms: float
    jitter_ms: float
    severity: float
    uncertainty: float
    target_present: bool
    approaching: bool
    deadline_ms: float
    provider_u: float # exogenous: NOT passed to policy

    def __post_init__(self):
        for name in ('t_s','latency_ms','jitter_ms','severity','uncertainty','deadline_ms','provider_u'):
            lower=1e-12 if name=='deadline_ms' else 0.
            upper=1. if name in ('severity','uncertainty','provider_u') else None
            number(getattr(self,name),name,lower=lower,upper=upper)
        if type(self.target_present) is not bool or type(self.approaching) is not bool:
            raise ValueError('target_present and approaching must be booleans')

    @classmethod
    def from_dict(cls, record):
        needed=set(cls.__dataclass_fields__)
        if set(record)!=needed:raise ValueError(f'observation fields mismatch: missing={sorted(needed-set(record))}, extra={sorted(set(record)-needed)}')
        return cls(**record)

    def observable(self):
        # No future/provider outcomes nor counterfactuals are ever passed to policies.
        return PolicyView(self.t_s,self.latency_ms,self.jitter_ms,self.severity,self.uncertainty,
                          self.target_present,self.approaching,self.deadline_ms)


@dataclass(frozen=True)
class PolicyView:
    t_s:float
    latency_ms:float
    jitter_ms:float
    severity:float
    uncertainty:float
    target_present:bool
    approaching:bool
    deadline_ms:float


@dataclass(frozen=True)
class Config:
    schema_version: str = '1.0'
    seed:int=42
    duration_s:float=60.
    tick_s:float=.1
    accept_probability:float=.8
    setup_delay_s:float=1.
    lease_s:float=10.
    cooldown_s:float=5.
    provider_timeout_probability:float=0.
    provider_service_unavailable_probability:float=0.
    qod_latency_factor:float=.67
    qod_jitter_factor:float=.8
    request_fee_units:float=1.
    active_second_units:float=.2
    deadline_miss_penalty_units:float=3.
    static_threshold:float=.6
    adaptive_gate:float=.15

    def __post_init__(self):
        if self.schema_version!='1.0':raise ValueError('unsupported schema_version')
        if isinstance(self.seed,bool) or not isinstance(self.seed,int) or self.seed<0:raise ValueError('seed must be a nonnegative integer')
        for name in ('duration_s','tick_s','setup_delay_s','lease_s','cooldown_s','request_fee_units','active_second_units','deadline_miss_penalty_units'):
            number(getattr(self,name),name,lower=(1e-12 if name in ('duration_s','tick_s','lease_s') else 0.))
        for name in ('accept_probability','provider_timeout_probability','provider_service_unavailable_probability','qod_latency_factor','qod_jitter_factor','static_threshold','adaptive_gate'):
            number(getattr(self,name),name,upper=1.,lower=(1e-12 if name.startswith('qod_') else 0.))
        if self.duration_s/self.tick_s > 100000: raise ValueError('too many simulated ticks')
        if self.accept_probability+self.provider_timeout_probability+self.provider_service_unavailable_probability > 1+1e-12:
            raise ValueError('accept + timeout + unavailable probabilities must be <= 1')

    @classmethod
    def from_dict(cls, d):
        allowed=set(cls.__dataclass_fields__)
        if set(d)-allowed:raise ValueError(f'unknown config fields: {sorted(set(d)-allowed)}')
        return cls(**d)