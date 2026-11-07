import unittest
from src.models.ipo_schema import (
    IPOProfile, IPOMeta, FinancialYear, IssueStructure,
    PeerComparison, GovernanceAndRisks, ExchangeCategory
)
from src.analyzers.governance_issue_analyzer import analyze_governance_and_structure


class TestGovernanceAnalyzer(unittest.TestCase):
    def test_clean_governance_and_high_fresh_issue(self):
        profile = IPOProfile(
            meta=IPOMeta("Clean IPO", "CLN", "Auto", ExchangeCategory.MAINBOARD, 100.0, 95.0, 100.0, 10, 500.0),
            financials=[FinancialYear("FY26", 500.0, 80.0, 50.0, 300.0, 20.0, 45.0)],
            issue_structure=IssueStructure(
                fresh_issue_crores=450.0,
                ofs_crores=50.0,
                promoter_pre_holding_pct=80.0,
                promoter_post_holding_pct=65.0,
                promoter_pledge_pct=0.0
            ),
            peers=PeerComparison(),
            governance=GovernanceAndRisks(
                pending_litigations_crores=2.0,
                contingent_liabilities_crores=1.0,
                auditor_qualifications=False
            )
        )
        res = analyze_governance_and_structure(profile)
        self.assertEqual(res.fresh_issue_pct, 90.0)
        self.assertEqual(res.promoter_pledge_pct, 0.0)
        self.assertFalse(res.auditor_qualification_flag)
        self.assertGreater(res.score, 80.0)

    def test_heavy_ofs_and_pledge_penalty(self):
        profile = IPOProfile(
            meta=IPOMeta("Trap IPO", "TRP", "Retail", ExchangeCategory.MAINBOARD, 100.0, 95.0, 100.0, 10, 1000.0),
            financials=[FinancialYear("FY26", 500.0, 40.0, 10.0, 100.0, 150.0, 5.0)],
            issue_structure=IssueStructure(
                fresh_issue_crores=100.0,
                ofs_crores=900.0,
                promoter_pre_holding_pct=75.0,
                promoter_post_holding_pct=30.0,
                promoter_pledge_pct=40.0
            ),
            peers=PeerComparison(),
            governance=GovernanceAndRisks(
                pending_litigations_crores=45.0,
                auditor_qualifications=True,
                promoter_legal_disputes=True
            )
        )
        res = analyze_governance_and_structure(profile)
        self.assertEqual(res.ofs_pct, 90.0)
        self.assertEqual(res.promoter_pledge_pct, 40.0)
        self.assertTrue(res.auditor_qualification_flag)
        self.assertLess(res.score, 30.0)
        self.assertTrue(any("Promoter/PE Exit Vehicle" in rf for rf in res.red_flags))


if __name__ == "__main__":
    unittest.main()
