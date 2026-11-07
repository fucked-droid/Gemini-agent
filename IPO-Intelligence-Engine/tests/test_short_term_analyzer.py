import unittest
from src.models.ipo_schema import (
    IPOProfile, IPOMeta, FinancialYear, IssueStructure,
    PeerComparison, GovernanceAndRisks, ShortTermListingMetrics, ExchangeCategory
)
from src.analyzers.short_term_listing_analyzer import analyze_short_term_listing


class TestShortTermListingAnalyzer(unittest.TestCase):
    def test_explosive_listing_gain(self):
        profile = IPOProfile(
            meta=IPOMeta("Frenzy IPO", "FRNZ", "Defense", ExchangeCategory.MAINBOARD, 300.0, 285.0, 300.0, 50, 600.0),
            financials=[],
            issue_structure=IssueStructure(500.0, 100.0, 80.0, 65.0),
            peers=PeerComparison(),
            governance=GovernanceAndRisks(),
            short_term=ShortTermListingMetrics(
                gmp_inr=150.0,
                gmp_trend="RISING",
                qib_subscription_times=65.0,
                nii_subscription_times=45.0,
                retail_subscription_times=20.0,
                total_subscription_times=40.0,
                anchor_quality="TIER_1_MARQUEE"
            )
        )
        res = analyze_short_term_listing(profile)
        self.assertEqual(res.gmp_pct, 50.0)
        self.assertEqual(res.expected_listing_price, 450.0)
        self.assertEqual(res.expected_profit_per_lot_inr, 7500.0)
        self.assertGreaterEqual(res.listing_score, 85.0)
        self.assertIn("9:15 AM", res.playbook.market_open_sell_rule)

    def test_discount_listing_trap(self):
        profile = IPOProfile(
            meta=IPOMeta("Trap IPO", "TRP", "Retail", ExchangeCategory.MAINBOARD, 500.0, 475.0, 500.0, 30, 2500.0),
            financials=[],
            issue_structure=IssueStructure(100.0, 2400.0, 75.0, 35.0),
            peers=PeerComparison(),
            governance=GovernanceAndRisks(),
            short_term=ShortTermListingMetrics(
                gmp_inr=-20.0,
                gmp_trend="FALLING",
                qib_subscription_times=0.8,
                total_subscription_times=0.9,
                anchor_quality="WEAK"
            )
        )
        res = analyze_short_term_listing(profile)
        self.assertEqual(res.gmp_pct, -4.0)
        self.assertLess(res.listing_score, 30.0)
        self.assertTrue(any("Negative GMP" in rf for rf in res.red_flags))
        self.assertIn("BAILOUT", res.playbook.market_open_sell_rule)


if __name__ == "__main__":
    unittest.main()
