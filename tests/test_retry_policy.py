import unittest
from types import SimpleNamespace
from qodpolicylab.retry_policy import RetryConfig,RetryGuard
from qodpolicylab.models import Config
from qodpolicylab.scenario import generate
from qodpolicylab.simulation import run
class RetryTests(unittest.TestCase):
    def fake(self):
        return SimpleNamespace(state='OBSERVE',requests=1,events=[],_clock_s=0.)
    def test_transient_backoff(self):
        s=self.fake();g=RetryGuard(RetryConfig())
        s.events.append({'t_s':1,'event':'TIMEOUT','request_id':1})
        g.observe(s)
        self.assertFalse(g.allowed(s,1.9));self.assertTrue(g.allowed(s,2))
        g.observe(s);self.assertEqual(len(g.audit),1)
    def test_denial_terminal(self):
        s=self.fake();g=RetryGuard(RetryConfig())
        s.events.append({'t_s':1,'event':'REJECT','request_id':1})
        g.observe(s);self.assertFalse(g.allowed(s,1e8))
    def test_huge_factor_does_not_overflow(self):
        s=self.fake();g=RetryGuard(RetryConfig(max_requests=1000,max_transient_failures=1000,
            initial_delay_s=.01,factor=1e300,max_delay_s=8))
        for i in range(1,100):
            s.events.append({'t_s':i,'event':'TIMEOUT','request_id':i})
        g.observe(s);self.assertAlmostEqual(g.next_allowed_s,107)
    def test_invalid_config(self):
        with self.assertRaises(ValueError): RetryConfig(max_requests=True)
        with self.assertRaises(ValueError): RetryConfig(factor=.5)
    def test_opt_in_integration(self):
        cfg=Config(duration_s=3,tick_s=.1,static_threshold=0,
                   accept_probability=0,provider_timeout_probability=1,
                   setup_delay_s=.1,cooldown_s=0)
        trace=generate(cfg)
        base=run(trace,cfg,'static')
        opt=run(trace,cfg,'static',retry_config=RetryConfig(max_requests=1))
        self.assertNotIn('retry_policy',base)
        self.assertIn('retry_policy',opt)
        self.assertLessEqual(opt['request_count'],1)
        self.assertTrue(all(not x['active'] for x in opt['rows']))
