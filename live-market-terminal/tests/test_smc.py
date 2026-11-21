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
        self.assertEqual(res["setup_type"], "INSUFFICIENT HISTORICAL DATA")
        self.assertEqual(res["status"], "INSUFFICIENT HISTORICAL DATA")

    def test_missing_candles_and_insufficient_history(self):
        # 1. None
        res_none = SMCAnalyzer.analyze_smc(None)
        self.assertFalse(res_none["has_smc_setup"])
        self.assertEqual(res_none["status"], "INSUFFICIENT HISTORICAL DATA")
        self.assertEqual(res_none["setup_type"], "INSUFFICIENT HISTORICAL DATA")

        # 2. Insufficient bars (< 10)
        short_df = self.df.iloc[:5]
        res_short = SMCAnalyzer.analyze_smc(short_df)
        self.assertFalse(res_short["has_smc_setup"])
        self.assertEqual(res_short["status"], "INSUFFICIENT HISTORICAL DATA")
        self.assertEqual(res_short["details_why_it_works"], ["INSUFFICIENT HISTORICAL DATA"])

    def test_invalid_ohlc_values_nan_inf_negative(self):
        # 1. NaN in price
        df_nan = self.df.copy()
        df_nan.loc[df_nan.index[10], "High"] = np.nan
        res_nan = SMCAnalyzer.analyze_smc(df_nan)
        self.assertFalse(res_nan["has_smc_setup"])
        self.assertEqual(res_nan["status"], "UNAVAILABLE — INVALID INPUT DATA")
        self.assertEqual(res_nan["setup_type"], "UNAVAILABLE — INVALID INPUT DATA")
        self.assertEqual(res_nan["details_why_it_works"], ["UNAVAILABLE — INVALID INPUT DATA"])

        # 2. Infinite value
        df_inf = self.df.copy()
        df_inf.loc[df_inf.index[15], "Close"] = np.inf
        res_inf = SMCAnalyzer.analyze_smc(df_inf)
        self.assertFalse(res_inf["has_smc_setup"])
        self.assertEqual(res_inf["status"], "UNAVAILABLE — INVALID INPUT DATA")

        # 3. Negative price
        df_neg = self.df.copy()
        df_neg.loc[df_neg.index[20], "Low"] = -50.0
        res_neg = SMCAnalyzer.analyze_smc(df_neg)
        self.assertFalse(res_neg["has_smc_setup"])
        self.assertEqual(res_neg["status"], "UNAVAILABLE — INVALID INPUT DATA")

        # 4. Inconsistent High < Low
        df_inv = self.df.copy()
        df_inv.loc[df_inv.index[5], "High"] = 24900.0
        df_inv.loc[df_inv.index[5], "Low"] = 25000.0
        res_inv = SMCAnalyzer.analyze_smc(df_inv)
        self.assertFalse(res_inv["has_smc_setup"])
        self.assertEqual(res_inv["status"], "UNAVAILABLE — INVALID INPUT DATA")

    def test_bos_choch_confirmation_gate(self):
        from analytics.market_structure import MarketStructureAnalyzer
        swings = MarketStructureAnalyzer.find_swings(self.df, window=2)
        bos_choch = SMCAnalyzer.detect_bos_and_choch(self.df, swings)
        bos = bos_choch.get("bos", {})
        choch = bos_choch.get("choch", {})

        # If confirmed, required levels must be valid numbers > 0
        if bos.get("confirmed"):
            self.assertGreater(bos.get("broken_level", 0), 0)
            self.assertGreater(bos.get("level", 0), 0)
            self.assertTrue(np.isfinite(bos.get("broken_level")))
        if choch.get("confirmed"):
            self.assertGreater(choch.get("broken_level", 0), 0)
            self.assertGreater(choch.get("level", 0), 0)
            self.assertTrue(np.isfinite(choch.get("broken_level")))

        # Test corrupt swings: BOS must not show confirmed
        corrupted_swings = {"swing_highs": [{"price": np.nan, "index": 5}], "swing_lows": []}
        corrupt_res = SMCAnalyzer.detect_bos_and_choch(self.df, corrupted_swings)
        self.assertFalse(corrupt_res["bos"]["confirmed"])
        self.assertFalse(corrupt_res["choch"]["confirmed"])

    def test_valid_structure_calculations(self):
        from analytics.market_structure import MarketStructureAnalyzer
        # Create zigzag price pattern for swing expansion detection: HH + HL
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
        self.assertEqual(struct["status"], "VALID")
        self.assertIn("EXPANSION", struct["structure_state"])
        self.assertEqual(struct["trend_type"], "BULLISH")
        self.assertGreater(struct["nearest_support"], 0.0)
        self.assertGreater(struct["nearest_resistance"], 0.0)
        self.assertTrue(all(np.isfinite(x) for x in struct["swing_highs"]))
        self.assertTrue(all(np.isfinite(x) for x in struct["swing_lows"]))

if __name__ == "__main__":
    unittest.main()
