import unittest
import os
from src.data_loader import load_ipo_from_json
from src.scoring_engine import evaluate_ipo
from src.models.ipo_schema import VerdictTier


class TestScoringEngineAndEndToEnd(unittest.TestCase):
    def setUp(self):
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

    def test_sample_mainboard_listing_pop(self):
        file_path = os.path.join(self.data_dir, "sample_mainboard_ipo.json")
        profile = load_ipo_from_json(file_path)
        ev = evaluate_ipo(profile)

        self.assertEqual(ev.verdict, VerdictTier.APPLY_LISTING_POP)
        self.assertGreaterEqual(ev.composite_score, 75.0)
        self.assertIn("APPLY FOR LISTING POP", ev.verdict_title)
        self.assertGreater(ev.expected_gain_pct, 30.0)
        self.assertGreater(ev.expected_profit_per_lot_inr, 5000.0)
        self.assertIn("9:15 AM", ev.playbook.market_open_sell_rule)

    def test_sample_avoid_trap(self):
        file_path = os.path.join(self.data_dir, "sample_avoid_trap_ipo.json")
        profile = load_ipo_from_json(file_path)
        ev = evaluate_ipo(profile)

        self.assertEqual(ev.verdict, VerdictTier.AVOID_DISCOUNT_TRAP)
        self.assertLess(ev.composite_score, 40.0)
        self.assertIn("AVOID", ev.verdict_title)
        self.assertLessEqual(ev.expected_gain_pct, 0.0)

    def test_sample_sme_listing_pop(self):
        file_path = os.path.join(self.data_dir, "sample_sme_ipo.json")
        profile = load_ipo_from_json(file_path)
        ev = evaluate_ipo(profile)

        self.assertTrue(ev.sme_res.is_sme)
        self.assertGreaterEqual(ev.composite_score, 75.0)
        self.assertEqual(ev.verdict, VerdictTier.APPLY_LISTING_POP)
        self.assertGreater(ev.expected_gain_pct, 50.0)
        self.assertGreater(ev.expected_profit_per_lot_inr, 50000.0)


if __name__ == "__main__":
    unittest.main()
