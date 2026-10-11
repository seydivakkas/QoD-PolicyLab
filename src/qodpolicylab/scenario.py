"""Precomputed exogenous trace; RNG draws never consumed by policy-specific requests."""
from __future__ import annotations
import json
import math
import random
from pathlib import Path
from .models import Config, Observation


def generate(config: Config):
    rng=random.Random(config.seed)
    length=int(math.floor(config.duration_s / config.tick_s + 1e-9))
    rows=[]
    for k in range(length):
        t=round(k*config.tick_s,9)
        # Bursts and correlated baseline latency shock; purely hypothetical model.
        burst=(k // 30) % 4 in (1,2)
        severity=max(0.,min(1.,(.78 if burst else .28)+rng.gauss(0,.09)))
        latency=max(0.,(105. if burst else 48.)+rng.gauss(0,11.))
        jitter=max(0.,(18. if burst else 5.)+rng.gauss(0,3.))
        target=(k//45)%3 != 2
        approaching=(k//21)%4 != 3
        deadline=85.
        u=rng.random() # indexed once per external time slot; no policy request consumes RNG
        rows.append(Observation(t,latency,jitter,severity,.15,target,approaching,deadline,u))
    return tuple(rows)


def write_trace(trace, path):
    from dataclasses import asdict
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8',newline='\n') as f:
        for row in trace:f.write(json.dumps(asdict(row),sort_keys=True,allow_nan=False)+'\n')


def read_trace(path):
    rows=[];prior=-math.inf
    with Path(path).open(encoding='utf-8') as f:
        for line in f:
            if not line.strip():continue
            obj=Observation.from_dict(json.loads(line))
            if obj.t_s<=prior: raise ValueError('trace timestamps must be strictly increasing')
            prior=obj.t_s;rows.append(obj)
    if not rows:raise ValueError('trace cannot be empty')
    if len(rows)>100000:raise ValueError('trace exceeds capacity')
    return tuple(rows)