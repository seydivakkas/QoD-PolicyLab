"""Offline seeded synthetic heavy-tail/handover stress generator.

Illustrative fading/handover mechanisms, NOT distributions fitted to 5G data.
Stable per-timestep randomness; all policies replay the identical observations.
"""
from __future__ import annotations
from dataclasses import dataclass
import random,math,argparse,json,hashlib
from pathlib import Path
from .models import Observation

@dataclass(frozen=True)
class TailConfig:
    base_latency_ms:float=48.
    lognormal_sigma:float=.42
    burst_probability:float=.035
    burst_persistence:float=.79
    handover_probability:float=.012
    pareto_shape:float=2.3
    pareto_scale_ms:float=65.
    max_latency_ms:float=10000.

    def __post_init__(self):
        for f in ('base_latency_ms','lognormal_sigma','burst_probability','burst_persistence',
                  'handover_probability','pareto_shape','pareto_scale_ms','max_latency_ms'):
            v=getattr(self,f)
            if isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) or v<0:
                raise ValueError('INVALID_TAIL_PARAMETER_'+f)
        if self.base_latency_ms<=0 or self.max_latency_ms<self.base_latency_ms or self.pareto_shape<=1:
            raise ValueError('INVALID_TAIL_SUPPORT')
        for n in ('burst_probability','burst_persistence','handover_probability'):
            if getattr(self,n)>1:raise ValueError('INVALID_TAIL_PROBABILITY')


def make_tail_trace(*,seed=501,n=1000,dt=.1,cfg:TailConfig|None=None):
    if type(seed) is not int or seed<0 or type(n) is not int or not 2<=n<=30000 or not math.isfinite(dt) or dt<=0:
        raise ValueError('INVALID_SYNTHETIC_TRACE_SETTINGS')
    cfg=cfg or TailConfig();rng=random.Random(seed);burst=False
    rows=[]
    for i in range(n):
        if burst:
            burst=rng.random()<cfg.burst_persistence
        elif rng.random()<cfg.burst_probability:
            burst=True
        handover=rng.random()<cfg.handover_probability
        baseline=cfg.base_latency_ms*rng.lognormvariate(-cfg.lognormal_sigma**2/2,cfg.lognormal_sigma)
        excursion=(cfg.pareto_scale_ms*rng.paretovariate(cfg.pareto_shape)) if burst else 0.
        if handover:excursion+=cfg.pareto_scale_ms*rng.paretovariate(cfg.pareto_shape)
        latency=min(cfg.max_latency_ms,baseline+excursion)
        rows.append({'timestamp_s':round(i*dt,9),'latency_ms':round(latency,6),
                     'jitter_ms':round(min(latency*.25,abs(rng.gauss(7.,4.))),6),
                     'burst':burst,'handover':handover,
                     'deadline_ms':100. if i%75<45 else 180.,
                     'target_present':i%75<52,'approaching':i%75<45,
                     'severity':round(min(1.,latency/250),6),
                     'uncertainty':round(min(1.,(.12 if not burst else .45)+(.25 if handover else 0.)),6),
                     'provider_u':rng.random()})
    return rows


def to_observations(rows):
    return [Observation(t_s=x['timestamp_s'],latency_ms=x['latency_ms'],jitter_ms=x['jitter_ms'],
                        severity=x['severity'],uncertainty=x['uncertainty'],
                        target_present=x['target_present'],approaching=x['approaching'],
                        deadline_ms=x['deadline_ms'],provider_u=x['provider_u']) for x in rows]


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=501)
    p.add_argument('--ticks',type=int,default=1000);p.add_argument('--out',required=True)
    a=p.parse_args(argv);path=Path(a.out)
    if path.exists():raise SystemExit('OUTPUT_EXISTS')
    rows=make_tail_trace(seed=a.seed,n=a.ticks)
    data=('\n'.join(json.dumps(v,sort_keys=True) for v in rows)+'\n').encode('utf-8')
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    manifest={'schema_version':'1.0','simulated':True,'seed':a.seed,'ticks':len(rows),
              'trace_sha256':hashlib.sha256(data).hexdigest(),
              'assumption':'illustrative lognormal + Pareto bursts + handover; not measured 5G'}
    path.with_suffix('.manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest))

if __name__=='__main__':main()
