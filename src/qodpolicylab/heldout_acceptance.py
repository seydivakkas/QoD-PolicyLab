"""Frozen synthetic holdout for causal QoD policy / retry / renewal behavior.

A negative control must never invent benefit; performance regressions remain
reported even if all structural tests pass. No operator API or SLA inference.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
from statistics import mean
from .models import Config
from .scenario import generate
from .simulation import run
from .retry_policy import RetryConfig

PROTOCOL = 'QOD-SYNTH-HOLDOUT-v1-20261012'
SEEDS = (14200,14201,14202,14203,14204,14205,14206,14207)
SCENARIOS = {
    'reference': {},
    'no_qod_effect': {'qod_latency_factor':1.,'qod_jitter_factor':1.},
    'no_grants': {'accept_probability':0.,'provider_timeout_probability':0.,'provider_service_unavailable_probability':0.},
    'provider_503': {'accept_probability':0.,'provider_timeout_probability':0.,'provider_service_unavailable_probability':1.},
    'long_setup': {'setup_delay_s':6.},
}
POLICIES=('best_effort','static','adaptive')
VARIANTS=('legacy','bounded_retry','async_renew_cancel')


def _delta(d, key):
    return [row[key] for row in d]


def evaluate_frozen():
    all_rows=[];violations=[]
    for scenario,overrides in SCENARIOS.items():
        for seed in SEEDS:
            cfg=Config(**{**asdict(Config(duration_s=20.,tick_s=.2,seed=seed)),**overrides})
            trace=generate(cfg)
            controls={}
            for policy in POLICIES:
                for variant in VARIANTS:
                    kwargs={}
                    if variant=='bounded_retry':
                        kwargs={'retry_config':RetryConfig(max_requests=3,max_transient_failures=2,
                                                              initial_delay_s=.4,factor=2.,max_delay_s=2.)}
                    elif variant=='async_renew_cancel':
                        kwargs={'callback_delay_s':.2,'request_timeout_s':3.,
                                'cancel_when_absent':True,'renew_before_s':.5,
                                'max_renewals':2,'max_requests':3}
                    result=run(trace,cfg,policy,**kwargs)
                    key=policy+'__'+variant
                    controls[key]=result
                    if variant!='legacy' and result['request_count']>3:
                        violations.append({'scenario':scenario,'seed':seed,'case':key,'failure':'REQUEST_BUDGET_EXCEEDED'})
                    if scenario in ('no_grants','provider_503') and any(r['active'] for r in result['rows']):
                        violations.append({'scenario':scenario,'seed':seed,'case':key,'failure':'FALSE_ACTIVE_PROVIDER_GAIN'})
                    if scenario=='no_qod_effect' and any(
                            abs(r['baseline_latency_ms']-r['latency_ms'])>1e-9 for r in result['rows']):
                        violations.append({'scenario':scenario,'seed':seed,'case':key,'failure':'FALSE_NO_EFFECT_GAIN'})
                    if not math.isfinite(result['service_cost_units']) or result['service_cost_units']<0:
                        violations.append({'scenario':scenario,'seed':seed,'case':key,'failure':'COST_NOT_FINITE'})
                    all_rows.append({'scenario':scenario,'seed':seed,'policy':policy,'variant':variant,
                                     'misses':result['deadline_misses'],'eligible':result['eligible_deadline_events'],
                                     'requests':result['request_count'],'renewals':result['renewal_count'],
                                     'cost_units':result['service_cost_units'],
                                     'utility_loss_units':result['utility_loss_units']})
            reference=controls['best_effort__legacy']
            for policy in ('static','adaptive'):
                for variant in VARIANTS:
                    r=controls[policy+'__'+variant]
                    # No invented promise that adaptive is always superior.
                    if r['eligible_deadline_events'] != reference['eligible_deadline_events']:
                        violations.append({'scenario':scenario,'seed':seed,'case':policy+'__'+variant,
                                           'failure':'UNPAIRED_ELIGIBLE_EVENTS'})
    grouped={}
    for row in all_rows:
        key=row['scenario']+'__'+row['policy']+'__'+row['variant']
        grouped.setdefault(key,[]).append(row)
    summary={key:{'mean_misses':mean(row['misses'] for row in rows),
                  'mean_cost_units':mean(row['cost_units'] for row in rows),
                  'mean_utility_loss_units':mean(row['utility_loss_units'] for row in rows),
                  'worst_seed_misses':max(row['misses'] for row in rows),
                  'worst_seed_cost_units':max(row['cost_units'] for row in rows)}
             for key,rows in sorted(grouped.items())}
    return {'schema_version':'1.0','protocol':PROTOCOL,'seed_set':list(SEEDS),
            'scenarios':list(SCENARIOS),'variants':list(VARIANTS),
            'rows':all_rows,'summary':summary,'invariants_pass':not violations,
            'violations':violations,'performance_acceptance':'NOT_ESTABLISHED',
            'backend_v1_decision':'HOLD',
            'negative_claim':'Static/adaptive may be worse than each other, or worse than Best Effort on cost. All results retained.',
            'real_operator_validated':False}


def write_frozen(path):
    """Create immutable JSON + checksum manifest; never overwrite prior evidence."""
    destination=Path(path)
    if destination.exists():
        raise FileExistsError('QOD_HOLDOUT_OUTPUT_ALREADY_EXISTS')
    report=evaluate_frozen()
    raw=(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n').encode('utf-8')
    manifest={'schema_version':'1.0','protocol':PROTOCOL,
              'source':'SYNTHETIC_ONLY','sha256':{'holdout.json':hashlib.sha256(raw).hexdigest()},
              'backend_v1_decision':'HOLD'}
    destination.mkdir(parents=True,exist_ok=False)
    (destination/'holdout.json').write_bytes(raw)
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf8')
    return manifest


def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(description='Immutable frozen synthetic QoD policy holdout')
    parser.add_argument('--out',required=True)
    args=parser.parse_args(argv)
    print(json.dumps(write_frozen(args.out)))

if __name__=='__main__':main()