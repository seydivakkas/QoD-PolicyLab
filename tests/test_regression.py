import json
import tempfile
import unittest
from pathlib import Path
from dataclasses import asdict
from qodpolicylab.models import Config, Observation
from qodpolicylab.scenario import generate
from qodpolicylab.session import Session
from qodpolicylab.simulation import run
from qodpolicylab.cli import main

class RegressionTests(unittest.TestCase):
    def test_state_machine_no_repeat_requests_while_cooldown(self):
        c=Config(accept_probability=1.,setup_delay_s=0.,lease_s=1.,cooldown_s=2.)
        s=Session(c);s.advance(0);s.request(0,0)
        self.assertEqual(s.state,'ACTIVE')
        with self.assertRaises(ValueError):s.request(.1,0)
        s.advance(1);self.assertEqual(s.state,'COOLDOWN')
        s.advance(2);self.assertEqual(s.state,'COOLDOWN')
        s.advance(3);self.assertEqual(s.state,'OBSERVE')
        self.assertEqual(s.requests,1)

    def test_provider_timeout_path(self):
        c=Config(accept_probability=0.,provider_timeout_probability=1.,static_threshold=0.,duration_s=12.)
        r=run(generate(c),c,'static')
        self.assertGreater(r['timeout_count'],0)
        self.assertEqual(r['accept_count'],0)
        self.assertTrue(all(not x['active'] for x in r['rows']))

    def test_trace_out_of_order_does_not_mutate_inputs(self):
        c=Config(duration_s=5.)
        t=generate(c)
        with self.assertRaises(ValueError):run((t[1],t[0]),c,'best_effort')
        self.assertEqual(t,generate(c))

    def test_invalid_observation_and_config(self):
        with self.assertRaises(ValueError):Observation.from_dict({'t_s':0})
        with self.assertRaises(ValueError):Config(duration_s=float('nan'))
        with self.assertRaises(ValueError):Config(qod_latency_factor=0.)
        with self.assertRaises(ValueError):Config(seed=True)

    def test_local_report(self):
        with tempfile.TemporaryDirectory() as td:
            cfg=Path(td)/'cfg.json';cfg.write_text(json.dumps(asdict(Config(duration_s=4.))),encoding='utf-8')
            out=Path(td)/'run'
            main(['compare','--config',str(cfg),'--seeds','2','--out',str(out)])
            main(['report','--run',str(out)])
            html=(out/'report.html').read_text(encoding='utf-8')
            self.assertIn('SIMULATED ONLY',html)
            self.assertNotIn('script src=',html)

if __name__=='__main__':unittest.main()