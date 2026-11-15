"""
Unit Tests for Technical Indicators.
Validates mathematical correctness of EMA 10/20, VWAP, RSI, MACD, ATR,
Bollinger Bands, Opening Range, and edge cases.
"""

import unittest
import numpy as np
import pandas as pd
import datetime

import sys
from pathlib import Path
TERMINAL_ROOT = Path(__file__).resolve().parent.parent
if str(TERMINAL_ROOT) not in sys.path:
    sys.path.insert(0, str(TERMINAL_ROOT))

from analytics.indicators import TechnicalIndicators

class TestTechnicalIndicators(unittest.TestCase):

    def setUp(self):
        # Generate 100 deterministic mock bars
        dates = [datetime.datetime(2026, 11, 14, 9, 15) + datetime.timedelta(minutes=5 * i) for i in range(100)]
        closes = [25000.0 + i * 2.0 for i in range(100)]
        highs = [c + 5.0 for c in closes]
        lows = [c - 5.0 for c in closes]
        opens = [c - 1.0 for c in closes]
        volumes = [10000 + i * 50 for i in range(100)]

        self.df = pd.DataFrame(
            {"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes},
            index=pd.DatetimeIndex(dates, name="Datetime"),
        )

    def test_ema_calculation(self):
        ema10 = TechnicalIndicators.compute_ema(self.df["Close"], 10)
        ema20 = TechnicalIndicators.compute_ema(self.df["Close"], 20)

        self.assertEqual(len(ema10), 100)
        # In a steady uptrend, EMA 10 must be greater than EMA 20
        self.assertGreater(ema10.iloc[-1], ema20.iloc[-1])
        # EMA must be close to current price
        self.assertAlmostEqual(ema10.iloc[-1], self.df["Close"].iloc[-1], delta=20.0)

    def test_vwap_calculation(self):
        vwap = TechnicalIndicators.compute_vwap(self.df)
        self.assertEqual(len(vwap), 100)
        self.assertFalse(vwap.isna().any())
        # VWAP should lie between session low and high
        self.assertGreaterEqual(vwap.iloc[-1], self.df["Low"].min())
        self.assertLessEqual(vwap.iloc[-1], self.df["High"].max())

    def test_vwap_zero_volume_resilience(self):
        df_zero = self.df.copy()
        df_zero["Volume"] = 0
        vwap = TechnicalIndicators.compute_vwap(df_zero)
        # Should not raise ZeroDivisionError and handle gracefully
        self.assertEqual(len(vwap), 100)

    def test_rsi_calculation(self):
        rsi = TechnicalIndicators.compute_rsi(self.df["Close"], 14)
        self.assertEqual(len(rsi), 100)
        # Monotonic uptrend RSI should be > 70
        self.assertGreater(rsi.iloc[-1], 70.0)
        # Bounded between 0 and 100
        self.assertGreaterEqual(rsi.min(), 0.0)
        self.assertLessEqual(rsi.max(), 100.0)

    def test_macd_calculation(self):
        macd, signal, hist = TechnicalIndicators.compute_macd(self.df["Close"], 12, 26, 9)
        self.assertEqual(len(macd), 100)
        self.assertEqual(len(signal), 100)
        self.assertEqual(len(hist), 100)
        # In uptrend, fast MACD line should be positive
        self.assertGreater(macd.iloc[-1], 0)

    def test_atr_calculation(self):
        atr = TechnicalIndicators.compute_atr(self.df, 14)
        self.assertEqual(len(atr), 100)
        # With high - low = 10, ATR should stabilize around 10
        self.assertAlmostEqual(atr.iloc[-1], 10.0, delta=2.0)

    def test_bollinger_bands(self):
        upper, mid, lower, pct_b = TechnicalIndicators.compute_bollinger_bands(self.df["Close"], 20, 2.0)
        self.assertGreater(upper.iloc[-1], mid.iloc[-1])
        self.assertGreater(mid.iloc[-1], lower.iloc[-1])

    def test_opening_range_breakout(self):
        or_data = TechnicalIndicators.compute_opening_range(self.df, 15)
        # In steady uptrend, current price > OR high
        self.assertEqual(or_data["status"], "BULLISH_BREAKOUT_ABOVE_ORH")
        self.assertGreater(or_data["current_price"], or_data["or_high"])

    def test_empty_dataframe_resilience(self):
        empty_df = pd.DataFrame()
        res_df, scalars = TechnicalIndicators.calculate_all(empty_df)
        self.assertTrue(res_df.empty)
        self.assertEqual(scalars, {})

if __name__ == "__main__":
    unittest.main()
