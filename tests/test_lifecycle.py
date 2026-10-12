import unittest
from qodpolicylab.session import Session
from qodpolicylab.models import Config


def config():
    return Config(lease_s=2.,setup_delay_s=.1,cooldown_s=.5,accept_probability=1.)

class LifecycleTests(unittest.TestCase):
    def test_cancel_pending_ignores_delayed_grant(self):
        s=Session(config(),auto_provider=False,request_timeout_s=5.)
        s.advance(0.);s.request(0.,0.)
        self.assertEqual(s.cancel(.05,1),'APPLIED')
        self.assertEqual(s.cancel(.05,1),'IGNORED_DUPLICATE')
        self.assertEqual(s.provider_callback(.2,1,'GRANT'),'IGNORED_DUPLICATE')
        self.assertEqual(s.accepts,0)
        s.advance(2.)
        self.assertEqual(s.state,'OBSERVE')
    def test_cancel_active_stops_future_benefit(self):
        s=Session(config())
        s.advance(0.);s.request(0.,0.);s.advance(.2)
        self.assertEqual(s.state,'ACTIVE')
        self.assertEqual(s.cancel(.25,1),'APPLIED')
        self.assertEqual(s.state,'COOLDOWN')
        self.assertIsNone(s.active_until)
        self.assertEqual(s.provider_callback(.3,1,'GRANT'),'IGNORED_DUPLICATE')
    def test_renewal_is_bounded_idempotent_and_expires_exactly(self):
        s=Session(config());s.advance(0.);s.request(0.,0.);s.advance(.1)
        self.assertEqual(s.renew(.2,1,token='a',extension_s=1.,max_renewals=1),'APPLIED')
        self.assertEqual(s.renew(.3,1,token='a',extension_s=1.,max_renewals=1),'IGNORED_DUPLICATE')
        self.assertEqual(s.renew(.3,1,token='b',extension_s=1.,max_renewals=1),'BUDGET_EXHAUSTED')
        self.assertAlmostEqual(s.active_until,3.1)
        s.advance(4.)
        self.assertEqual([e['t_s'] for e in s.events if e['event']=='LEASE_EXPIRED'],[3.1])
    def test_invalid_renewal_and_expired_session(self):
        s=Session(config());s.advance(0.);s.request(0.,0.);s.advance(.1)
        with self.assertRaisesRegex(ValueError,'RENEW_INVALID_EXTENSION'):
            s.renew(.2,1,token='x',extension_s=float('nan'))
        self.assertEqual(s.renew(5.,1,token='x',extension_s=1.),'IGNORED_STALE')
    def test_retry_policy_is_not_silent(self):
        s=Session(config(),auto_provider=False,request_timeout_s=.3)
        s.advance(0.);s.request(0.,0.);s.advance(1.)
        self.assertEqual(s.timeouts,1)
        self.assertEqual(s.state,'OBSERVE')
        # Explicit caller decision needed; no hidden retry is created.
        self.assertEqual(s.requests,1)

if __name__=='__main__':unittest.main()

class LifecyclePolicyIntegrationTests(unittest.TestCase):
    def test_opt_in_renewal_and_cancel_are_causal(self):
        from qodpolicylab.models import Observation
        from qodpolicylab.simulation import run
        c=Config(lease_s=1.,setup_delay_s=0.,cooldown_s=2.,tick_s=.5,
                 accept_probability=1.,static_threshold=0.,duration_s=3.)
        def obs(t,has_target):
            return Observation(t,120.,1.,1.,1.,has_target,True,50.,0.)
        trace=[obs(0,True),obs(.5,True),obs(1.,True),obs(1.5,False),obs(2.,False)]
        plain=run(trace,c,'static')
        enhanced=run(trace,c,'static',renew_before_s=.6,max_renewals=1,cancel_when_absent=True)
        self.assertEqual(enhanced['renewal_count'],1)
        self.assertTrue(enhanced['rows'][3]['cancelled'])
        self.assertFalse(enhanced['rows'][3]['active'])
        self.assertEqual(len([x for x in enhanced['sessions'] if x['event']=='RENEW']),1)
        self.assertGreaterEqual(enhanced['service_cost_units'], plain['service_cost_units'])
    def test_budget_and_invalid_flag(self):
        from qodpolicylab.simulation import run
        with self.assertRaisesRegex(ValueError,'renew_before_s'):
            run([],config(),'static',renew_before_s=3.)
        with self.assertRaisesRegex(ValueError,'cancel_when_absent'):
            run([],config(),'static',cancel_when_absent='yes')