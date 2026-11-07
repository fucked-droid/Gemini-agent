import unittest
import os
from src.data_loader import load_ipo_from_json
from src.scoring_engine import evaluate_ipo
from src.models.ipo_schema import VerdictTier


class TestScoringEngineAndEndToEnd(unittest.TestCase):
    def setUp(self):
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

    def test_sample_mainboard_compounder(self):
        file_path = os.path.join(self.data_dir, "sample_mainboard_ipo.json")
        profile = load_ipo_from_json(file_path)
        ev = evaluate_ipo(profile)

        self.assertEqual(ev.verdict, VerdictTier.STRONG_BUY)
        self.assertGreaterEqual(ev.composite_score, 75.0)
        self.assertIn("LONG-TERM COMPOUNDER", ev.verdict_title)
        self.assertFalse(ev.financial_res.negative_cfo_flag)
        self.assertGreater(ev.financial_res.latest_roce_pct, 20.0)

    def test_sample_avoid_trap(self):
        file_path = os.path.join(self.data_dir, "sample_avoid_trap_ipo.json")
        profile = load_ipo_from_json(file_path)
        ev = evaluate_ipo(profile)

        self.assertEqual(ev.verdict, VerdictTier.AVOID_TRAP)
        self.assertLess(ev.composite_score, 45.0)
        self.assertIn("AVOID / PROMOTER CASH-OUT TRAP", ev.verdict_title)
        self.assertTrue(ev.financial_res.negative_cfo_flag)
        self.assertGreater(ev.governance_res.ofs_pct, 80.0)

    def test_sample_sme_ipo(self):
        file_path = os.path.join(self.data_dir, "sample_sme_ipo.json")
        profile = load_ipo_from_json(file_path)
        ev = evaluate_ipo(profile)

        self.assertTrue(ev.sme_res.is_sme)
        self.assertGreaterEqual(ev.composite_score, 60.0)
        self.assertIn(ev.verdict, (VerdictTier.STRONG_BUY, VerdictTier.BUY_ON_DIPS))


if __name__ == "__main__":
    unittest.main()
