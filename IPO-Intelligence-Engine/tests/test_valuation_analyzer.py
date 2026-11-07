import unittest
from src.models.ipo_schema import (
    IPOProfile, IPOMeta, FinancialYear, IssueStructure,
    PeerComparison, PeerInfo, GovernanceAndRisks, ExchangeCategory
)
from src.analyzers.valuation_analyzer import analyze_valuation


class TestValuationAnalyzer(unittest.TestCase):
    def setUp(self):
        self.profile = IPOProfile(
            meta=IPOMeta(
                company_name="Alpha Tech",
                symbol="ALPHA",
                sector="IT Services",
                category=ExchangeCategory.MAINBOARD,
                issue_price=200.0,
                price_band_low=190.0,
                price_band_high=200.0,
                lot_size=75,
                issue_size_crores=500.0
            ),
            financials=[
                FinancialYear("FY24", 200.0, 40.0, 25.0, 100.0, 20.0, 22.0),
                FinancialYear("FY25", 280.0, 60.0, 40.0, 140.0, 25.0, 36.0),
                FinancialYear("FY26", 400.0, 90.0, 65.0, 205.0, 30.0, 60.0)
            ],
            issue_structure=IssueStructure(
                fresh_issue_crores=400.0,
                ofs_crores=100.0,
                promoter_pre_holding_pct=85.0,
                promoter_post_holding_pct=70.0
            ),
            peers=PeerComparison(
                peers=[
                    PeerInfo("Peer 1", 35.0, 5.0, 20.0),
                    PeerInfo("Peer 2", 45.0, 7.0, 25.0)
                ],
                industry_pe_median=40.0
            ),
            governance=GovernanceAndRisks()
        )

    def test_valuation_discount(self):
        # Public holding = 30% -> Implied Mcap = 500 / 0.30 = 1666.67 Cr
        # Latest PAT = 65 Cr -> Implied PE = 1666.67 / 65 = 25.64x
        # Industry median = 40.0x -> Discount = (25.64 - 40) / 40 = -35.9% (DEEP_DISCOUNT)
        res = analyze_valuation(self.profile, pat_cagr=60.0)
        self.assertAlmostEqual(res.implied_pe, 25.64, delta=0.5)
        self.assertEqual(res.valuation_status, "DEEP_DISCOUNT")
        self.assertLess(res.valuation_premium_pct, -25.0)
        self.assertLess(res.peg_ratio, 1.0)
        self.assertGreater(res.score, 80.0)

    def test_exorbitant_greed_valuation(self):
        # Change PAT to very small (e.g., 5.0 Cr) -> Implied PE becomes huge
        self.profile.financials[-1].pat_crores = 5.0
        res = analyze_valuation(self.profile, pat_cagr=10.0)
        self.assertGreater(res.implied_pe, 150.0)
        self.assertEqual(res.valuation_status, "EXORBITANT_PREMIUM")
        self.assertLess(res.score, 30.0)


if __name__ == "__main__":
    unittest.main()
