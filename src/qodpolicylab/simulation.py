"""Counterfactual policy runner, per-seed paired comparison and audit metrics."""
from __future__ import annotations
from dataclasses import asdict
import math
from statistics import mean
from .models import Config
from .policies import decide
from .session import Session
from .scenario import generate
from .stats import paired_bootstrap

POLICIES=('best_effort','static','adaptive')


def quantile(values,q):
    s=sorted(values)
    if not s:return None
    k=(len(s)-1)*q
    lo=int(math.floor(k));hi=int(math.ceil(k))
    return float(s[lo]+(s[hi]-s[lo])*(k-lo))


def run(trace, cfg:Config, policy):
    if policy not in POLICIES:raise ValueError('invalid policy')
    session=Session(cfg)
    rows=[];last=-math.inf
    for k,obs in enumerate(trace):
        if obs.t_s<=last:raise ValueError('trace timestamps must be strictly increasing')
        last=obs.t_s
        session.advance(obs.t_s)
        request=False
        if session.state=='OBSERVE':
            request=decide(policy,obs.observable(),cfg)
            if request:session.request(obs.t_s,obs.provider_u)
        active=session.state=='ACTIVE'
        # Exogenous observation is shared, and QoD is an endogenous modeled effect.
        latency_ms=obs.latency_ms*(cfg.qod_latency_factor if active else 1.)
        jitter_ms=obs.jitter_ms*(cfg.qod_jitter_factor if active else 1.)
        eligible=obs.target_present and obs.approaching
        miss=bool(eligible and latency_ms>obs.deadline_ms)
        # Tick duration is deterministic per config; no provider time is backdated.
        session.account_active(cfg.tick_s)
        rows.append({'t_s':obs.t_s,'baseline_latency_ms':obs.latency_ms,'latency_ms':latency_ms,
                     'jitter_ms':jitter_ms,'deadline_ms':obs.deadline_ms,'eligible':eligible,
                     'miss':miss,'state':session.state,'request':request,'active':active})
    eligible_count=sum(v['eligible'] for v in rows)
    misses=sum(v['miss'] for v in rows)
    service=session.requests*cfg.request_fee_units+session.active_seconds*cfg.active_second_units
    result={'schema_version':'1.0','model':'hypothetical QoD; not actual 5G service','policy':policy,'seed':cfg.seed,
            'ticks':len(rows),'p50_latency_ms':quantile([r['latency_ms'] for r in rows],.5),
            'p95_latency_ms':quantile([r['latency_ms'] for r in rows],.95),
            'p99_latency_ms':quantile([r['latency_ms'] for r in rows],.99),
            'eligible_deadline_events':eligible_count,'deadline_misses':misses,
            'deadline_miss_rate':misses/eligible_count if eligible_count else None,
            'request_count':session.requests,'accept_count':session.accepts,
            'rejection_count':session.rejects,'timeout_count':session.timeouts,'service_unavailable_count':session.service_unavailable,
            'active_time_s':session.active_seconds,'service_cost_units':service,
            'utility_loss_units':service+misses*cfg.deadline_miss_penalty_units,
            'rows':rows,'sessions':session.events}
    return result


def compare(cfg:Config, seeds=30):
    if not isinstance(seeds,int) or not 1<=seeds<=1000:raise ValueError('seeds must be 1..1000')
    trials=[]
    for seed in range(cfg.seed,cfg.seed+seeds):
        local=Config(**{**asdict(cfg),'seed':seed})
        trace=generate(local)
        scores={policy:run(trace,local,policy) for policy in POLICIES}
        trial={'seed':seed}
        for policy,s in scores.items():
            trial[policy+'_miss_rate']=s['deadline_miss_rate']
            trial[policy+'_service_cost_units']=s['service_cost_units']
            trial[policy+'_request_count']=s['request_count']
        trial['adaptive_minus_be_misses']=scores['adaptive']['deadline_misses']-scores['best_effort']['deadline_misses']
        trial['adaptive_minus_static_misses']=scores['adaptive']['deadline_misses']-scores['static']['deadline_misses']
        trials.append(trial)
    return {'schema_version':'1.0','seed_start':cfg.seed,'seed_count':seeds,'policies':POLICIES,
            'paired_trials':trials,'paired_bootstrap_misses':{name:paired_bootstrap([v[name] for v in trials],seed=cfg.seed) for name in ('adaptive_minus_be_misses','adaptive_minus_static_misses')} if seeds>=2 else None,'summary':{
                policy:{'average_miss_rate':mean(v[policy+'_miss_rate'] for v in trials if v[policy+'_miss_rate'] is not None),
                        'average_service_cost_units':mean(v[policy+'_service_cost_units'] for v in trials)}
                for policy in POLICIES},'claim':'synthetic paired descriptive comparison; not measured operator QoD'}