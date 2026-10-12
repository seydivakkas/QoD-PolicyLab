"""Synthetic provider fault and callback corruption tests: no telecom API."""
import unittest
from qodpolicylab.models import Config
from qodpolicylab.session import Session
from qodpolicylab.simulation import run
from qodpolicylab.scenario import generate
from qodpolicylab.experiments import sweep


class CallbackTests(unittest.TestCase):
    def test_duplicate_and_late_grant_never_reactivate(self):
        c=Config(setup_delay_s=1,lease_s=1,cooldown_s=1,accept_probability=1.)
        s=Session(c);s.advance(0);s.request(0,0.)
        with self.assertRaisesRegex(ValueError,'precede'):
            s.provider_callback(.1,1,'GRANT')
        self.assertEqual(s.requests,1)
        self.assertEqual(s.provider_callback(1,1,'GRANT'),'APPLIED')
        self.assertEqual(s.provider_callback(1.1,1,'GRANT'),'IGNORED_DUPLICATE')
        self.assertEqual(s.accepts,1)
        s.advance(2)
        self.assertEqual(s.state,'COOLDOWN')
        self.assertEqual(s.provider_callback(2.5,1,'GRANT'),'IGNORED_DUPLICATE')
        self.assertEqual(s.state,'COOLDOWN')
        s.advance(3)
        s.request(3,0.)
        self.assertEqual(s.provider_callback(4,1,'REJECT'),'IGNORED_DUPLICATE')
        self.assertEqual(s.provider_callback(4,2,'GRANT'),'APPLIED')
        self.assertEqual(s.accepts,2)

    def test_invalid_unknown_callbacks(self):
        c=Config(setup_delay_s=2)
        s=Session(c);s.advance(0);s.request(0,.1)
        for bad in (0, 2, True, -1):
            with self.assertRaises(ValueError):s.provider_callback(2,bad,'GRANT')
        with self.assertRaises(ValueError):s.provider_callback(float('nan'),1,'GRANT')
        with self.assertRaises(ValueError):s.provider_callback(2,1,'INVALID')
        self.assertEqual(s.state,'REQUESTING')
        self.assertEqual(s.accepts,0)

    def test_forced_503_fallback_no_qod_benefit(self):
        c=Config(seed=8,duration_s=10,static_threshold=0.,
                 accept_probability=0.,provider_timeout_probability=0.,
                 provider_service_unavailable_probability=1.,setup_delay_s=.2)
        result=run(generate(c),c,'static')
        self.assertGreater(result['service_unavailable_count'],0)
        self.assertEqual(result['accept_count'],0)
        self.assertEqual(result['rejection_count'],0)
        self.assertEqual(result['timeout_count'],0)
        self.assertTrue(all(not x['active'] and x['baseline_latency_ms']==x['latency_ms'] for x in result['rows']))
        self.assertTrue(any(e['event']=='SERVICE_UNAVAILABLE' for e in result['sessions']))
        with self.assertRaises(ValueError):Config(accept_probability=.5,provider_timeout_probability=.3,provider_service_unavailable_probability=.3)

    def test_predeclared_unavailable_sweep(self):
        result=sweep(Config(seed=6,duration_s=3.),seeds=2)
        self.assertIn('all_service_unavailable',[p['profile'] for p in result['profiles']])

if __name__=='__main__':unittest.main()