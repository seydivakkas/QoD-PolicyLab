import tempfile
import unittest
from pathlib import Path
from qodpolicylab.stats import paired_bootstrap
from qodpolicylab.models import Config
from qodpolicylab.experiments import sweep,PROFILES
from qodpolicylab.cli import main

class StatsTests(unittest.TestCase):
 def test_bootstrap_determinism_and_equal_effect(self):
  r=paired_bootstrap([2,2,2,2],seed=3,draws=200)
  self.assertEqual(r,paired_bootstrap([2,2,2,2],seed=3,draws=200))
  self.assertEqual(r['p025'],2)
  self.assertEqual(r['p975'],2)
 def test_short_samples_rejected(self):
  with self.assertRaises(ValueError):paired_bootstrap([1])
 def test_sweep_negative_controls(self):
  cfg=Config(seed=10,duration_s=8.)
  r=sweep(cfg,seeds=3)
  self.assertEqual(len(r['profiles']),len(PROFILES))
  zero=next(x for x in r['profiles'] if x['profile']=='no_qod_effect')
  self.assertIsNotNone(zero['paired_bootstrap_misses'])
  with tempfile.TemporaryDirectory() as td:
   main(['sweep','--seeds','2','--out',str(Path(td)/'sweep')])
   self.assertTrue((Path(td)/'sweep'/'sweep.json').exists())