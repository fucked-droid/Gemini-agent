import unittest
from src.models.ipo_schema import FinancialYear
from src.analyzers.financial_analyzer import analyze_financials


class TestFinancialAnalyzer(unittest.TestCase):
    def setUp(self):
        self.robust_fin = [
            FinancialYear("FY24", 100.0, 20.0, 10.0, 50.0, 10.0, 10.0, 20.0, 20.0),
            FinancialYear("FY25", 130.0, 28.0, 15.0, 65.0, 12.0, 14.0, 22.0, 23.0),
            FinancialYear("FY26", 169.0, 40.0, 22.5, 87.5, 15.0, 21.0, 25.0, 25.7)
        ]

    def test_cagr_calculation(self):
        res = analyze_financials(self.robust_fin)
        # 100 to 169 over 2 periods is 30% CAGR
        self.assertAlmostEqual(res.revenue_cagr_pct, 30.0, delta=0.5)
        # 10 to 22.5 over 2 periods is 50% CAGR
        self.assertAlmostEqual(res.pat_cagr_pct, 50.0, delta=0.5)
        self.assertEqual(res.ebitda_margin_trend, "EXPANDING")
        self.assertFalse(res.negative_cfo_flag)
        self.assertGreater(res.score, 75.0)

    def test_negative_cfo_penalty(self):
        bleeding_fin = [
            FinancialYear("FY24", 100.0, 15.0, 8.0, 50.0, 100.0, -10.0, 8.0, 8.0),
            FinancialYear("FY25", 110.0, 16.0, 9.0, 55.0, 150.0, -25.0, 7.0, 7.0),
            FinancialYear("FY26", 115.0, 18.0, 10.0, 60.0, 200.0, -40.0, 6.0, 6.0)
        ]
        res = analyze_financials(bleeding_fin)
        self.assertTrue(res.negative_cfo_flag)
        self.assertLess(res.score, 40.0)
        self.assertTrue(any("Bleeding operating cash flow" in rf for rf in res.red_flags))
        self.assertGreater(res.latest_debt_to_equity, 3.0)

    def test_empty_financials_resilience(self):
        res = analyze_financials([])
        self.assertEqual(res.score, 0.0)
        self.assertTrue(res.negative_cfo_flag)


if __name__ == "__main__":
    unittest.main()
