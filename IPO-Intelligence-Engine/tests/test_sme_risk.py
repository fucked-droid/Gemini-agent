import unittest
from src.models.ipo_schema import (
    IPOProfile, IPOMeta, FinancialYear, IssueStructure,
    PeerComparison, GovernanceAndRisks, SMERiskMetrics, ExchangeCategory
)
from src.analyzers.sme_risk_analyzer import analyze_sme_risk


class TestSMERiskAnalyzer(unittest.TestCase):
    def test_mainboard_bypass(self):
        profile = IPOProfile(
            meta=IPOMeta("Mainboard Corp", "MBC", "Infra", ExchangeCategory.MAINBOARD, 250.0, 240.0, 250.0, 60, 800.0),
            financials=[],
            issue_structure=IssueStructure(800.0, 0.0, 80.0, 65.0),
            peers=PeerComparison(),
            governance=GovernanceAndRisks()
        )
        res = analyze_sme_risk(profile)
        self.assertFalse(res.is_sme)
        self.assertEqual(res.score, 100.0)

    def test_sme_concentration_risk(self):
        profile = IPOProfile(
            meta=IPOMeta("SME High Risk", "SMER", "Chemicals", ExchangeCategory.SME_NSE, 120.0, 115.0, 120.0, 1200, 30.0),
            financials=[],
            issue_structure=IssueStructure(30.0, 0.0, 90.0, 68.0),
            peers=PeerComparison(),
            governance=GovernanceAndRisks(),
            sme_metrics=SMERiskMetrics(
                is_sme=True,
                top_3_clients_revenue_pct=78.0,
                top_5_clients_revenue_pct=88.0,
                debtor_days=140.0,
                working_capital_days=160.0
            )
        )
        res = analyze_sme_risk(profile)
        self.assertTrue(res.is_sme)
        self.assertEqual(res.customer_concentration_risk, "CRITICAL")
        self.assertLess(res.score, 40.0)
        self.assertTrue(any("Severe Client Concentration" in rf for rf in res.red_flags))
        self.assertTrue(any("Stretched Receivable Cycle" in rf for rf in res.red_flags))


if __name__ == "__main__":
    unittest.main()
