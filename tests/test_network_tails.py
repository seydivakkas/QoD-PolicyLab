import unittest
from qodpolicylab.network_tails import TailConfig,make_tail_trace,to_observations
class TailTests(unittest.TestCase):
 def test_seed_and_monotonic(self):
  a=make_tail_trace(seed=99,n=100);b=make_tail_trace(seed=99,n=100)
  self.assertEqual(a,b);self.assertEqual(len(to_observations(a)),100)
  self.assertTrue(all(x['latency_ms']>0 for x in a))
  self.assertTrue(all(a[i]['timestamp_s']<a[i+1]['timestamp_s'] for i in range(99)))
 def test_heavy_tail_and_handover(self):
  c=TailConfig(burst_probability=1.,burst_persistence=1.,handover_probability=1.)
  a=make_tail_trace(seed=1,n=80,cfg=c)
  self.assertTrue(any(x['burst'] for x in a));self.assertTrue(all(x['handover'] for x in a))
 def test_config_rejects_invalid(self):
  with self.assertRaises(ValueError):TailConfig(pareto_shape=.9)
