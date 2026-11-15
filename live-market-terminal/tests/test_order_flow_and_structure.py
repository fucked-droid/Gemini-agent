"""
Unit Tests for Order Flow (CVD) and Market Structure Analytics.
Validates delta decomposition, buyer pressure ratios, absorption divergences,
and fractal swing identification.
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

from analytics.order_flow import OrderFlowAnalyzer
from analytics.market_structure import MarketStructureAnalyzer

class TestOrderFlowAndStructure(unittest.TestCase):

    def setUp(self):
        dates = [datetime.datetime(2026, 11, 14, 9, 15) + datetime.timedelta(minutes=5 * i) for i in range(50)]

        # Alternating candles with strong buyer wicks
        opens = [25000.0 + i * 5.0 for i in range(50)]
        closes = [o + 6.0 for o in opens]  # strong green bars
        highs = [c + 2.0 for c in closes]
        lows = [o - 1.0 for o in opens]
        volumes = [50000 for _ in range(50)]

        self.df_bullish = pd.DataFrame(
            {"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes},
            index=pd.DatetimeIndex(dates, name="Datetime"),
        )

    def test_volume_delta_decomposition(self):
        df_flow = OrderFlowAnalyzer.compute_volume_delta(self.df_bullish)

        self.assertIn("Buy_Volume", df_flow.columns)
        self.assertIn("Sell_Volume", df_flow.columns)
        self.assertIn("Delta", df_flow.columns)
        self.assertIn("CVD", df_flow.columns)

        # In strong green bars, Buy Volume > Sell Volume and Delta > 0
        self.assertTrue((df_flow["Delta"] > 0).all())
        # CVD must be strictly increasing
        self.assertGreater(df_flow["CVD"].iloc[-1], df_flow["CVD"].iloc[0])

    def test_order_flow_analysis_classification(self):
        res = OrderFlowAnalyzer.analyze_order_flow(self.df_bullish)

        self.assertIn(res["order_flow_state"], ["STRONG_BULLISH_FLOW", "MODERATE_BULLISH_FLOW"])
        self.assertGreater(res["buyer_percentage"], 55.0)
        self.assertGreater(res["cvd"], 0)

    def test_market_structure_swings(self):
        # Create zigzag price pattern for swing detection: 10, 20, 10, 30, 15, 40
        closes = [
            10, 12, 15, 20, 18, 14, 10,  # Peak at 20, Trough at 10
            15, 22, 28, 30, 25, 20, 15,  # Peak at 30 (HH), Trough at 15 (HL)
            22, 32, 38, 42, 36, 30, 25   # Peak at 42 (HH)
        ]
        times = [datetime.datetime(2026, 11, 14, 9, 15) + datetime.timedelta(minutes=5 * i) for i in range(len(closes))]
        df_zigzag = pd.DataFrame({
            "Open": closes,
            "High": [c + 1 for c in closes],
            "Low": [c - 1 for c in closes],
            "Close": closes,
            "Volume": 1000
        }, index=pd.DatetimeIndex(times))

        struct = MarketStructureAnalyzer.analyze_structure(df_zigzag)

        self.assertEqual(struct["trend_type"], "BULLISH")
        self.assertIn("BULLISH", struct["structure_state"])
        self.assertGreater(struct["nearest_resistance"], 0.0)
        self.assertGreater(struct["nearest_support"], 0.0)

if __name__ == "__main__":
    unittest.main()
