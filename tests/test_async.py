import json
import tempfile
import unittest
from pathlib import Path
from qodpolicylab.models import Config
from qodpolicylab.scenario import generate
from qodpolicylab.simulation import run,compare
from qodpolicylab.event_driver import ProviderEventQueue
from qodpolicylab.decision_audit import pareto_frontier
from qodpolicylab.cli import main

class AsyncTests(unittest.TestCase):
    def test_async_delivery_and_no_backdated_grant(self):
        cfg=Config(seed=1,duration_s=6,tick_s=.1,setup_delay_s=.5,static_threshold=0,
                   accept_probability=1.,provider_timeout_probability=0.)
        res=run(generate(cfg),cfg,'static',callback_delay_s=.2,request_timeout_s=2.)
        self.assertGreater(res['accept_count'],0)
        self.assertTrue(all(e['outcome']=='GRANT' for e in res['callback_audit']))
        first=next(r for r in res['rows'] if r['active'])
        self.assertGreaterEqual(first['t_s'],.7)

    def test_late_grants_cannot_create_benefit(self):
        cfg=Config(seed=1,duration_s=5,tick_s=.1,setup_delay_s=.5,static_threshold=0,
                   accept_probability=1.,provider_timeout_probability=0.)
        res=run(generate(cfg),cfg,'static',callback_delay_s=1.,request_timeout_s=.6)
        self.assertEqual(res['accept_count'],0)
        self.assertGreater(res['timeout_count'],0)
        self.assertTrue(all(not x['active'] and x['latency_ms']==x['baseline_latency_ms'] for x in res['rows']))
        self.assertTrue(all(x['delivery_status']=='IGNORED_DUPLICATE' for x in res['callback_audit']))

    def test_default_unchanged_and_pareto_non_dominated(self):
        cfg=Config(seed=11,duration_s=3.)
        a=run(generate(cfg),cfg,'static')
        self.assertNotIn('callback_audit',a)
        audit=compare(cfg,seeds=4)
        self.assertIn('pareto_frontier',audit)
        self.assertIn('worst_seed',audit)
        self.assertEqual(pareto_frontier({'a':{'mean_miss_rate':.1,'mean_service_cost_units':3.},
                                          'b':{'mean_miss_rate':.3,'mean_service_cost_units':4.}}),['a'])

    def test_async_cli_manifest_and_invalid_args(self):
        cfg=Config(duration_s=2.,static_threshold=0,accept_probability=1.)
        with self.assertRaises(ValueError):run(generate(cfg),cfg,'static',callback_delay_s=.1)
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            trace=tmp/'trace.jsonl'
            from qodpolicylab.scenario import write_trace
            write_trace(generate(cfg),trace)
            main(['simulate','--trace',str(trace),'--policy','static','--callback-delay-s','1',
                  '--request-timeout-s','.5','--out',str(tmp/'out')])
            self.assertIn('callback_audit.json',json.loads((tmp/'out/manifest.json').read_text())['sha256'])

if __name__=='__main__':unittest.main()