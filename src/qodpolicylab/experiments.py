"""Predeclared synthetic negative-control and provider failure sweeps."""
from __future__ import annotations
from dataclasses import asdict
from .models import Config
from .simulation import compare

PROFILES={
    'baseline':{},
    'no_qod_effect':{'qod_latency_factor':1.,'qod_jitter_factor':1.},
    'always_rejected':{'accept_probability':0.,'provider_timeout_probability':0.},
    'all_timeouts':{'accept_probability':0.,'provider_timeout_probability':1.},
    'always_granted':{'accept_probability':1.,'provider_timeout_probability':0.},
    'slow_setup':{'setup_delay_s':3.},
}


def sweep(config:Config, seeds=30):
    rows=[]
    for name,change in PROFILES.items():
        cfg=Config(**{**asdict(config),**change})
        outcome=compare(cfg,seeds=seeds)
        rows.append({'profile':name,'parameters':change,'summary':outcome['summary'],
                     'paired_trials':outcome['paired_trials'],
                     'paired_bootstrap_misses':outcome.get('paired_bootstrap_misses')})
    return {'schema_version':'1.0','seed_start':config.seed,'seed_count':seeds,'profiles':rows,
            'interpretation':'synthetic predeclared policy profiles, not provider SLA tests'}