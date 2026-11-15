"""
Unit Tests for Smart Money Concepts (SMC) Analytics Engine.
Tests Fair Value Gaps (FVG), Liquidity Sweeps, Order Blocks (OB),
Fixed Structural Entry calculations, and Reversal Threat Analysis.
"""

import unittest
import pandas as pd
import numpy as np
import datetime
import sys
from pathlib import Path

TERMINAL_ROOT = Path(__file__).resolve().parent.parent
if str(TERMINAL_ROOT) not in sys.path:
    sys.path.insert(0, str(TERMINAL_ROOT))

from analytics.smc import SMCAnalyzer

class TestSMCAnalyzer(unittest.TestCase):

    def setUp(self):
        # Build 30 candles of price action with an explicit Bullish FVG and Liquidity Sweep
        times = [datetime.datetime(2026, 11, 14, 9, 15) + datetime.timedelta(minutes=5 * i) for i in range(30)]

        opens = [25000.0] * 30
        highs = [25010.0] * 30
        lows = [24990.0] * 30
        closes = [25005.0] * 30
        volumes = [10000] * 30

        # Create a swing low at bar 5: low = 24950.0
        lows[5] = 24950.0
        closes[5] = 24960.0

        # Bar 10 sweeps low of bar 5 (sweep low = 24940.0) but closes at 24970.0 (SSL Sweep!)
        lows[10] = 24940.0
        closes[10] = 24970.0
        opens[10] = 24965.0

        # Bar 11 is down candle / Order Block: open 24970, close 24965, low 24960, high 24975
        opens[11] = 24970.0
        closes[11] = 24965.0
        lows[11] = 24960.0
        highs[11] = 24975.0

        # Bars 12 & 13 show strong impulsive expansion creating a Bullish FVG
        # Bar 11 High is 24975.0. Bar 13 Low is 25010.0 (FVG gap: 24975 to 25010!)
        opens[12] = 24970.0
        closes[12] = 25020.0
        lows[12] = 24970.0
        highs[12] = 25025.0

        opens[13] = 25020.0
        closes[13] = 25060.0
        lows[13] = 25010.0
        highs[13] = 25070.0

        for k in range(14, 30):
            opens[k] = 25060.0 + (k - 14) * 5.0
            closes[k] = opens[k] + 4.0
            highs[k] = closes[k] + 3.0
            lows[k] = opens[k] - 2.0

        self.df = pd.DataFrame({
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": volumes
        }, index=pd.DatetimeIndex(times))

    def test_detect_fair_value_gaps(self):
        fvgs = SMCAnalyzer.detect_fair_value_gaps(self.df)
        self.assertIn("bullish_fvgs", fvgs)
        self.assertIn("bearish_fvgs", fvgs)

        # We deliberately created a bullish FVG at bar 12 (c0=bar 11 high: 24975, c2=bar 13 low: 25010)
        self.assertTrue(len(fvgs["bullish_fvgs"]) > 0)
        first_fvg = fvgs["bullish_fvgs"][0]
        self.assertEqual(first_fvg["type"], "BULLISH_FVG")
        self.assertGreater(first_fvg["top"], first_fvg["bottom"])
        self.assertGreaterEqual(first_fvg["consequent_encroachment"], first_fvg["bottom"])

    def test_detect_liquidity_sweeps(self):
        from analytics.market_structure import MarketStructureAnalyzer
        swings = MarketStructureAnalyzer.find_swings(self.df, window=2)
        sweeps = SMCAnalyzer.detect_liquidity_sweeps(self.df, swings, lookback_bars=25)

        self.assertIn("ssl_sweep", sweeps)
        self.assertIn("bsl_sweep", sweeps)
        self.assertIn("has_sweep", sweeps)

    def test_fixed_entry_smc_analysis(self):
        res = SMCAnalyzer.analyze_smc(self.df)

        self.assertTrue(res["has_smc_setup"])
        self.assertGreater(res["fixed_entry_price"], 0.0)
        self.assertGreater(res["fixed_stop_loss"], 0.0)
        self.assertGreater(res["fixed_target_1"], res["fixed_entry_price"])
        self.assertGreater(res["fixed_target_2"], res["fixed_target_1"])

        # Details why it works must be present and rich
        self.assertTrue(len(res["details_why_it_works"]) >= 1)
        self.assertTrue(any("LIQUIDITY" in d or "ORDER BLOCK" in d or "FAIR VALUE GAP" in d or "HIGHER-LOW" in d for d in res["details_why_it_works"]))

        # Reversal risk analysis must be present with % chance, threats, and invalidation trigger
        rev = res["reversal_risk"]
        self.assertIn("chance_pct", rev)
        self.assertIn("risk_level", rev)
        self.assertIn("threats", rev)
        self.assertIn("invalidation_trigger", rev)
        self.assertTrue(len(rev["threats"]) > 0)

    def test_empty_dataframe_resilience(self):
        empty_df = pd.DataFrame()
        res = SMCAnalyzer.analyze_smc(empty_df)
        self.assertFalse(res["has_smc_setup"])
        self.assertEqual(res["setup_type"], "INSUFFICIENT_DATA")

if __name__ == "__main__":
    unittest.main()
