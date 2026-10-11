"""Transparent multi-objective comparison; no synthetic-policy superiority claim."""
from __future__ import annotations
import math


def pareto_frontier(points):
    """Minimize both mean missed-event rate and service expenditure."""
    for name,score in points.items():
        values=(score['mean_miss_rate'],score['mean_service_cost_units'])
        if any(not isinstance(v,(float,int)) or not math.isfinite(v) or v<0 for v in values):
            raise ValueError(f'nonfinite Pareto objective for {name}')
    non_dominated=[]
    for name,v in sorted(points.items()):
        dominated=any(
            (w['mean_miss_rate']<=v['mean_miss_rate'] and
             w['mean_service_cost_units']<=v['mean_service_cost_units'] and
             (w['mean_miss_rate']<v['mean_miss_rate'] or w['mean_service_cost_units']<v['mean_service_cost_units']))
            for other,w in points.items() if other != name)
        if not dominated:non_dominated.append(name)
    return non_dominated


def worst_seed_report(trials, policies):
    if not trials:raise ValueError('cannot audit an empty trial list')
    result={}
    for policy in policies:
        filtered=[r for r in trials if r[policy+'_miss_rate'] is not None]
        if not filtered:
            result[policy]={'status':'NO_ELIGIBLE_EVENTS'}
        else:
            worst=max(filtered,key=lambda r:(r[policy+'_miss_rate'],r[policy+'_service_cost_units'],-r['seed']))
            result[policy]={'status':'OBSERVED','seed':worst['seed'],
                            'miss_rate':worst[policy+'_miss_rate'],
                            'service_cost_units':worst[policy+'_service_cost_units']}
    return result