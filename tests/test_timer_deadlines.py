"""Synthetic exact-deadline and bounded-retry invariants for offline simulator."""
import unittest
from qodpolicylab.models import Config
from qodpolicylab.session import Session
from qodpolicylab.scenario import generate
from qodpolicylab.simulation import run


class TimerDeadlinesTests(unittest.TestCase):
    def test_coarse_tick_keeps_lease_expiry_and_cooldown_deadlines(self):
        cfg=Config(setup_delay_s=.2,lease_s=.5,cooldown_s=.4,
                   accept_probability=1.,provider_timeout_probability=0.)
        s=Session(cfg)
        s.advance(0.)
        s.request(0.,0.)
        s.advance(3.)
        events={e['event']:e['t_s'] for e in s.events}
        self.assertAlmostEqual(events['GRANT'],.2)
        self.assertAlmostEqual(events['LEASE_EXPIRED'],.7)
        self.assertAlmostEqual(events['COOLDOWN_END'],1.1)
        self.assertEqual(s.state,'OBSERVE')

    def test_external_timeout_exact_and_late_grant_cannot_resurrect(self):
        cfg=Config(setup_delay_s=.2,lease_s=1.,cooldown_s=.3)
        s=Session(cfg,auto_provider=False,request_timeout_s=.35)
        s.advance(0.)
        s.request(0.,0.)
        s.advance(2.)
        self.assertEqual(s.provider_callback(2.,1,'GRANT'),'IGNORED_DUPLICATE')
        self.assertEqual(s.accepts,0)
        self.assertEqual(s.timeouts,1)
        self.assertEqual(s.state,'OBSERVE')
        self.assertAlmostEqual([e['t_s'] for e in s.events if e['event']=='TIMEOUT'][0],.35)
        with self.assertRaisesRegex(ValueError,'backwards'):
            s.advance(1.)

    def test_bounded_request_attempts_and_config_validation(self):
        cfg=Config(seed=21,duration_s=6.,tick_s=.5,static_threshold=0.,
                   accept_probability=0.,cooldown_s=0.,setup_delay_s=.1)
        trace=generate(cfg)
        result=run(trace,cfg,'static',max_requests=2)
        self.assertLessEqual(result['request_count'],2)
        self.assertEqual(result['request_budget']['max_requests'],2)
        with self.assertRaisesRegex(ValueError,'max_requests'):
            run(trace,cfg,'static',max_requests=0)

    def test_no_full_tick_service_cost_beyond_lease(self):
        cfg=Config(seed=3,duration_s=2.,tick_s=.5,setup_delay_s=0.,lease_s=.1,
                   static_threshold=0.,cooldown_s=5.,accept_probability=1.)
        result=run(generate(cfg),cfg,'static')
        self.assertLessEqual(result['active_time_s'],.1+1e-9)


if __name__=='__main__':unittest.main()
