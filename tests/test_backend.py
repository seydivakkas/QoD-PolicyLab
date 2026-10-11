import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from qodpolicylab.models import Config,Observation
from qodpolicylab.scenario import generate,read_trace,write_trace
from qodpolicylab.policies import decide
from qodpolicylab.simulation import run,compare
from qodpolicylab.cli import main

class BackendTests(unittest.TestCase):
    def setUp(self):
        self.c=Config(seed=23,duration_s=12.,tick_s=.1,setup_delay_s=1.,lease_s=3.,cooldown_s=1.)
        self.trace=generate(self.c)

    def test_same_seed_byte_stable(self):
        self.assertEqual(self.trace,generate(self.c))
        self.assertNotEqual(self.trace,generate(Config(seed=24,duration_s=12.)))

    def test_policy_eligibility_and_boundaries(self):
        obs=Observation(0,100,10,.6,.1,True,True,90,.4)
        self.assertTrue(decide('static',obs.observable(),self.c))
        self.assertFalse(decide('static',Observation(0,100,10,.59,.1,True,True,90,.4).observable(),self.c))
        self.assertFalse(decide('adaptive',Observation(0,100,10,1,0,False,True,90,.4).observable(),self.c))
        self.assertFalse(decide('best_effort',obs.observable(),self.c))
        self.assertFalse(hasattr(obs.observable(),'provider_u'))

    def test_best_effort_no_service_cost(self):
        r=run(self.trace,self.c,'best_effort')
        self.assertEqual(r['request_count'],0)
        self.assertEqual(r['service_cost_units'],0)
        self.assertEqual(r['active_time_s'],0)

    def test_provider_always_rejects_and_fallback(self):
        c=Config(seed=1,duration_s=12.,accept_probability=0.,setup_delay_s=1.,static_threshold=0.)
        r=run(generate(c),c,'static')
        self.assertGreater(r['request_count'],0)
        self.assertEqual(r['accept_count'],0)
        self.assertTrue(all(not row['active'] for row in r['rows']))
        self.assertTrue(all(row['latency_ms']==row['baseline_latency_ms'] for row in r['rows']))

    def test_no_benefit_factor_one(self):
        c=Config(seed=11,duration_s=12.,accept_probability=1.,qod_latency_factor=1.,static_threshold=0.)
        r=run(generate(c),c,'static')
        self.assertGreater(r['active_time_s'],0)
        self.assertTrue(all(row['latency_ms']==row['baseline_latency_ms'] for row in r['rows']))

    def test_setup_delay_cannot_backdate(self):
        c=Config(seed=13,duration_s=15.,setup_delay_s=3.,accept_probability=1.,static_threshold=0.)
        r=run(generate(c),c,'static')
        requests=[v['t_s'] for v in r['sessions'] if v['event']=='REQUEST']
        grants=[v['t_s'] for v in r['sessions'] if v['event']=='GRANT']
        self.assertGreater(len(grants),0)
        self.assertGreaterEqual(grants[0]-requests[0],3.-1e-6)
        self.assertFalse(any(v['active'] for v in r['rows'] if v['t_s']<grants[0]))

    def test_provider_indexed_by_external_time_not_request_order(self):
        c=Config(seed=9,duration_s=12.,static_threshold=0.,accept_probability=.3)
        t=generate(c)
        a=run(t,c,'static');b=run(t,c,'adaptive')
        self.assertEqual([r['baseline_latency_ms'] for r in a['rows']],[r['baseline_latency_ms'] for r in b['rows']])
        self.assertEqual(a,run(t,c,'static'))

    def test_trace_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'trace.jsonl';write_trace(self.trace,p)
            self.assertEqual(tuple(self.trace),read_trace(p))
            p.write_text(json.dumps(asdict(self.trace[0]))+'\n'+json.dumps(asdict(self.trace[0]))+'\n',encoding='utf-8')
            with self.assertRaises(ValueError):read_trace(p)
        with self.assertRaises(ValueError): Config(accept_probability=.9,provider_timeout_probability=.5)

    def test_compare_and_cli_artifacts(self):
        c=Config(seed=4,duration_s=12.)
        r=compare(c,seeds=3)
        self.assertEqual(len(r['paired_trials']),3)
        with tempfile.TemporaryDirectory() as td:
            cfg=Path(td)/'cfg.json';cfg.write_text(json.dumps(asdict(c)),encoding='utf-8')
            main(['generate','--config',str(cfg),'--out',str(Path(td)/'trace')])
            main(['simulate','--config',str(cfg),'--trace',str(Path(td)/'trace'/'scenario.jsonl'),'--policy','static','--out',str(Path(td)/'sim')])
            main(['compare','--config',str(cfg),'--seeds','3','--out',str(Path(td)/'compare')])
            self.assertTrue((Path(td)/'compare'/'manifest.json').exists())
            self.assertTrue((Path(td)/'sim'/'network_realization.csv').exists())

if __name__=='__main__':unittest.main()