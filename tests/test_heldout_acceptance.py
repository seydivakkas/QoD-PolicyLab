import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from qodpolicylab.heldout_acceptance import evaluate_frozen, write_frozen,SEEDS,SCENARIOS,VARIANTS,POLICIES

class HeldoutAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.report=evaluate_frozen()
    def test_all_predeclared_scenario_seeds_and_approaches_are_included(self):
        rows=self.report['rows']
        self.assertEqual(len(rows),len(SEEDS)*len(SCENARIOS)*len(VARIANTS)*len(POLICIES))
        self.assertEqual(len({(r['scenario'],r['seed'],r['policy'],r['variant']) for r in rows}),len(rows))
        self.assertEqual(self.report['seed_set'],list(SEEDS))
    def test_negative_controls_are_fail_closed(self):
        self.assertTrue(self.report['invariants_pass'],self.report['violations'][:3])
        self.assertFalse(self.report['real_operator_validated'])
        self.assertEqual(self.report['backend_v1_decision'],'HOLD')
        self.assertEqual(self.report['performance_acceptance'],'NOT_ESTABLISHED')
    def test_no_bounded_variant_exceeds_request_budget(self):
        self.assertTrue(all(r['requests']<=3 for r in self.report['rows'] if r['variant']!='legacy'))
        self.assertTrue(all(r['renewals']==0 for r in self.report['rows'] if r['variant']!='async_renew_cancel'))
    def test_complete_immutable_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'frozen'
            manifest=write_frozen(dest)
            self.assertEqual(hashlib.sha256((dest/'holdout.json').read_bytes()).hexdigest(),manifest['sha256']['holdout.json'])
            with self.assertRaisesRegex(FileExistsError,'OUTPUT_ALREADY_EXISTS'):write_frozen(dest)

if __name__=='__main__':unittest.main()