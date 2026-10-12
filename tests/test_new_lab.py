import unittest
from qodpolicylab.ttc_policy import compute_ttc_with_uncertainty,qos_decision,simulate_pareto
class Cases(unittest.TestCase):
 def test_closing(self):
  t=compute_ttc_with_uncertainty([20,0],[-5,0],[[.1,0],[0,.1]],[[.02,0],[0,.02]])
  self.assertEqual(t['status'],'VALID');self.assertAlmostEqual(t['ttc_s'],4)
 def test_failsafe(self):
  t=compute_ttc_with_uncertainty([3,0],[-10,0],[[.1,0],[0,.1]],[[.1,0],[0,.1]])
  a=qos_decision(t,latency_p99_ms=300,setup_delay_s=1.)
  self.assertEqual(a['action'],'LOCAL_FAILSAFE_REQUIRED')
 def test_not_collision(self):
  a=simulate_pareto([{'deadline_ms':100,'latency_ms':150,'p99_ms':200,'ttc_lower_s':2}])
  self.assertEqual(a['risk_metric'],'deadline miss only (not physical collision probability)')
