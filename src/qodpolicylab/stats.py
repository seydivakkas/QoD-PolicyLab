"""Paired per-scenario-seed bootstrap of policy effects, never per-tick pseudo-replication."""
from __future__ import annotations
import random
from statistics import mean


def paired_bootstrap(deltas, *, seed=42, draws=1000):
    x=[float(v) for v in deltas]
    if len(x)<2 or any(not -1e100<v<1e100 for v in x):
        raise ValueError('need >=2 finite paired scenario-seed effects')
    if not isinstance(draws,int) or not 100<=draws<=100000:
        raise ValueError('bootstrap draws must be 100..100000')
    rng=random.Random(seed)
    samples=sorted(mean(x[rng.randrange(len(x))] for _ in x) for _ in range(draws))
    def q(p):
        v=(len(samples)-1)*p;i=int(v);j=min(i+1,len(samples)-1)
        return samples[i]+(samples[j]-samples[i])*(v-i)
    return {'mean':mean(x),'p025':q(.025),'p975':q(.975),'unit':'deadline misses per scenario',
            'replication_unit':'independent scenario seed','draws':draws,'bootstrap_seed':seed}