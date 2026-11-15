"""
Automated Validation Suite for Institutional Trading Terminal Audit & Repairs.
Tests:
1. Instrument switching and strict data isolation (NIFTY, BANKNIFTY, BTC).
2. Timeframe switching and bar resampling.
3. WebSocket disconnection, reconnection, and state tracking.
4. Stale price and tick stalling detection (> 15 seconds).
5. Missing options data and graceful degradation to UNAVAILABLE.
6. Missing market data handling without unhandled exceptions.
7. CVD calculation parity (Candle delta, Timeframe CVD, Session CVD).
8. Signal invalidation logic and dynamic explanations.
9. Risk/reward calculation and mathematical expectancy consistency.
10. Historical vs. Live data separation (never showing LIVE when provider is offline).
"""

import os
import sys
import time
import datetime
import unittest
from pathlib import Path
import pandas as pd
import numpy as np

os.environ["TESTING"] = "1"

TERMINAL_ROOT = Path(__file__).resolve().parent.parent
if str(TERMINAL_ROOT) not in sys.path:
    sys.path.insert(0, str(TERMINAL_ROOT))

from data.market_status_manager import (
    MarketStatusManager,
    MarketDataStatus,
    get_market_status_manager,
)
from data.market_cache import MarketCache, get_global_cache
from data.historical_data import HistoricalDataManager
from data.dhan_client import DhanClient
from analytics.order_flow import OrderFlowAnalyzer
from analytics.options_analytics import OptionsAnalytics
from analytics.performance_analytics import PerformanceAnalytics
from analytics.indicators import TechnicalIndicators
from analytics.market_structure import MarketStructureAnalyzer
from analytics.smc import SMCAnalyzer
from signals.decision_engine import TradingDecisionEngine
import web_server


class TestAuditRepairs(unittest.TestCase):
    """
    Exhaustive functional and regression tests ensuring 100% compliance
    with institutional market engine guardrails.
    """

    def setUp(self):
        self.mgr = get_market_status_manager()
        self.cache = get_global_cache()

    # ==========================================================
    # 1. STRICT INSTRUMENT DATA ISOLATION & SWITCHING
    # ==========================================================
    def test_instrument_switching_and_isolation(self):
        """Verifies market data, breadth, and options are isolated by instrument."""
        # Process NIFTY
        web_server.process_symbol_pipeline("NIFTY")
        nifty_analytics = self.cache.analytics.get("NIFTY", {})
        self.assertIn("market_intelligence", nifty_analytics)
        self.assertNotEqual(nifty_analytics.get("market_breadth", {}).get("status"), "NOT_APPLICABLE")

        # Process BTC (Crypto Dev Test)
        web_server.process_symbol_pipeline("BTC")
        btc_analytics = self.cache.analytics.get("BTC", {})
        self.assertIn("market_intelligence", btc_analytics)
        # BTC must NEVER pollute with Indian equity breadth
        self.assertEqual(btc_analytics.get("market_breadth", {}).get("status"), "NOT_APPLICABLE")
        # BTC options must be strictly UNAVAILABLE
        self.assertEqual(btc_analytics.get("options_intelligence", {}).get("status"), "NO_CRYPTO_OPTIONS")

        # Process BANKNIFTY
        web_server.process_symbol_pipeline("BANKNIFTY")
        bn_analytics = self.cache.analytics.get("BANKNIFTY", {})
        self.assertIn("market_intelligence", bn_analytics)

        # Ensure cache structures are completely separate instances
        self.assertIsNot(nifty_analytics, btc_analytics)
        self.assertIsNot(nifty_analytics, bn_analytics)

    # ==========================================================
    # 2. TIMEFRAME SWITCHING & RESAMPLING
    # ==========================================================
    def test_timeframe_switching_and_aggregation(self):
        """Verifies multi-timeframe suite generates 1m, 3m, 5m, 15m without data corruption."""
        # Generate 60 synthetic 1m candles
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        idx = [now - datetime.timedelta(minutes=60 - i) for i in range(60)]
        df_1m = pd.DataFrame({
            "Open": [25000 + i for i in range(60)],
            "High": [25010 + i for i in range(60)],
            "Low": [24990 + i for i in range(60)],
            "Close": [25005 + i for i in range(60)],
            "Volume": [1000 for _ in range(60)],
        }, index=pd.DatetimeIndex(idx))

        suite = HistoricalDataManager.build_timeframe_suite(df_1m)
        self.assertIn("1m", suite)
        self.assertIn("3m", suite)
        self.assertIn("5m", suite)
        self.assertIn("15m", suite)

        # 60 1-minute bars should aggregate into 12 5-minute bars
        df_5m = suite["5m"]
        self.assertGreaterEqual(len(df_5m), 11)
        self.assertLessEqual(len(df_5m), 13)

        # Total volume must be preserved across resampled bars
        self.assertEqual(df_1m["Volume"].sum(), df_5m["Volume"].sum())

    # ==========================================================
    # 3. WEBSOCKET DISCONNECTION & RECONNECTION
    # ==========================================================
    def test_websocket_disconnection_and_reconnection(self):
        """Tests WebSocket state transitions from CONNECTED to RECONNECTING to CONNECTED."""
        # Set to connected
        self.mgr.set_websocket_status(True, "CONNECTED")
        self.assertTrue(self.mgr.websocket_connected)
        self.assertEqual(self.mgr.websocket_state, "CONNECTED")

        # Simulate connection drop
        self.mgr.set_websocket_status(False, "RECONNECTING")
        self.assertFalse(self.mgr.websocket_connected)
        status_info = self.mgr.get_status("NIFTY")
        self.assertEqual(status_info["status"], MarketDataStatus.RECONNECTING.value)

        # Re-establish
        self.mgr.set_websocket_status(True, "CONNECTED")
        self.assertTrue(self.mgr.websocket_connected)

    # ==========================================================
    # 4. STALE DATA DETECTION
    # ==========================================================
    def test_stale_data_detection(self):
        """Verifies feed flags STALE when ticks are stalled (> 15s) during active sessions."""
        sym = "BTC"  # 24/7 active session
        # Record tick 25 seconds in the past
        past_time = time.time() - 25.0
        self.mgr.record_tick(sym, past_time)

        status_info = self.mgr.get_status(sym)
        self.assertEqual(status_info["status"], MarketDataStatus.STALE.value)
        self.assertTrue(status_info["is_stale"])
        self.assertGreater(status_info["last_tick_delta_seconds"], 15.0)

        # Send fresh tick
        self.mgr.record_tick(sym, time.time())
        status_info_fresh = self.mgr.get_status(sym)
        self.assertEqual(status_info_fresh["status"], MarketDataStatus.LIVE.value)
        self.assertFalse(status_info_fresh["is_stale"])

    # ==========================================================
    # 5. MISSING OPTIONS DATA & GRACEFUL DEGRADATION
    # ==========================================================
    def test_missing_options_data_graceful_degradation(self):
        """Ensures options analytics returns UNAVAILABLE when live feed is absent."""
        # Unauthenticated offline mode for BANKNIFTY
        res = OptionsAnalytics.get_options_intelligence("BANKNIFTY", spot_price=51200.0, allow_sample=False)
        self.assertIsInstance(res, dict)
        self.assertEqual(res["sentiment"], "Unavailable")
        self.assertIn(res["status"], ["UNAVAILABLE", "NO_CRYPTO_OPTIONS"])
        self.assertIsNone(res["pcr_oi"])
        self.assertIsNone(res["max_pain"])
        self.assertEqual(res["key_strikes"], [])

    # ==========================================================
    # 6. MISSING MARKET DATA / EMPTY DATAFRAME HANDLING
    # ==========================================================
    def test_missing_market_data_handling(self):
        """Ensures all analytics engines handle empty / degenerate DataFrames gracefully."""
        empty_df = pd.DataFrame()

        # Indicators
        df_ind, ind_dict = TechnicalIndicators.calculate_all(empty_df)
        self.assertIsInstance(ind_dict, dict)

        # Order Flow
        flow = OrderFlowAnalyzer.analyze_order_flow(empty_df)
        self.assertEqual(flow["cvd"], 0)
        self.assertEqual(flow["order_flow_state"], "NEUTRAL")

        # Market Structure
        struct = MarketStructureAnalyzer.analyze_structure(empty_df)
        self.assertIn("NEUTRAL", struct.get("structure_state", "NEUTRAL"))

        # SMC
        smc = SMCAnalyzer.analyze_smc(empty_df)
        self.assertFalse(smc.get("has_smc_setup", False))

        # Decision Engine with empty internals
        dec = TradingDecisionEngine.evaluate(
            spot_price=25000.0,
            indicators={},
            mtf_data={},
            order_flow={},
            market_structure={},
            market_breadth={},
        )
        self.assertIsInstance(dec, dict)
        self.assertEqual(dec["decision"], "WAIT")

    # ==========================================================
    # 7. CVD CALCULATION & SHARED RECONCILIATION
    # ==========================================================
    def test_cvd_calculation_consistency(self):
        """Verifies candle delta, timeframe CVD, and session CVD mathematical consistency."""
        df = pd.DataFrame({
            "Open": [100.0, 102.0, 101.0, 103.0, 102.0, 104.0],
            "High": [105.0, 104.0, 106.0, 105.0, 106.0, 107.0],
            "Low": [99.0, 100.0, 101.0, 101.0, 100.0, 103.0],
            "Close": [104.0, 101.0, 105.0, 104.0, 105.0, 106.0],
            "Volume": [1000, 2000, 1500, 1200, 1800, 1400],
        })

        df_flow = OrderFlowAnalyzer.compute_volume_delta(df)
        self.assertIn("Buy_Volume", df_flow.columns)
        self.assertIn("Sell_Volume", df_flow.columns)
        self.assertIn("Delta", df_flow.columns)
        self.assertIn("CVD", df_flow.columns)

        # Verify bar delta = Buy_Volume - Sell_Volume
        for _, row in df_flow.iterrows():
            self.assertEqual(row["Delta"], row["Buy_Volume"] - row["Sell_Volume"])

        # Verify CVD is cumulative sum of Delta
        self.assertEqual(int(df_flow["CVD"].iloc[-1]), int(df_flow["Delta"].sum()))

        # Test shared analyze_order_flow with session_df
        flow = OrderFlowAnalyzer.analyze_order_flow(df, session_df=df)
        self.assertEqual(flow["session_cvd"], int(df_flow["CVD"].iloc[-1]))
        self.assertEqual(flow["timeframe_cvd"], int(df_flow["CVD"].iloc[-1]))
        self.assertEqual(flow["candle_delta"], int(df_flow["Delta"].iloc[-1]))

    # ==========================================================
    # 8. SIGNAL INVALIDATION & 4-PILLAR REASONING
    # ==========================================================
    def test_signal_invalidation_and_dynamic_explanations(self):
        """Verifies framework_breakdown separates HTF bias, Intraday, Entry, and Invalidation."""
        dec = TradingDecisionEngine.evaluate(
            spot_price=25150.0,
            indicators={"vwap": 25140.0, "ema10": 25145.0, "ema20": 25135.0, "atr": 50.0},
            mtf_data={"composite_trend": "BULLISH", "bullish_timeframes": 4, "bearish_timeframes": 1},
            order_flow={"order_flow_state": "STRONG_BULLISH_FLOW", "buyer_percentage": 56.0, "divergence": "NONE"},
            market_structure={"structure_state": "BULLISH_EXPANSION", "event": "BOS_UP"},
            market_breadth={"breadth_score": 0.40, "advances": 35, "declines": 15},
            buy_priority_mode=True,
        )

        self.assertIn("framework_breakdown", dec)
        fb = dec["framework_breakdown"]
        self.assertIn("higher_timeframe_bias", fb)
        self.assertIn("intraday_trend", fb)
        self.assertIn("entry_confirmation", fb)
        self.assertIn("trade_invalidation", fb)

        # Verify invalidation triggers are actionable
        self.assertGreater(len(fb["trade_invalidation"]["triggers"]), 0)
        self.assertIn("Trade Invalidation:", " ".join(dec["trade_decision_reasons"]))

    # ==========================================================
    # 9. RISK / REWARD & EXPECTANCY MATHEMATICAL CONSISTENCY
    # ==========================================================
    def test_performance_mathematical_consistency(self):
        """Verifies win rate, accuracy, profit factor, and expectancy mathematical formulas."""
        perf = PerformanceAnalytics.get_performance_metrics("NIFTY")
        self.assertIsInstance(perf, dict)

        # If live unverified, status must be explicitly DEMO_UNVERIFIED
        self.assertIn(perf["status"], ["LIVE_VERIFIED_AUDIT", "DEMO_UNVERIFIED"])
        if not perf["is_verified"]:
            self.assertIn("DEMO", perf["badge_text"])
            self.assertIn("UNVERIFIED", perf["badge_text"])

        # Mathematical Expectancy Verification: E = (Win% * AvgWin_R) - (Loss% * AvgLoss_R)
        total = perf["total_setups_evaluated"]
        wins = perf["wins_count"]
        losses = perf["losses_count"]
        win_r = perf["avg_win_r"]
        loss_r = perf["avg_loss_r"]

        calc_exp = round(((wins / total) * win_r) - ((losses / total) * loss_r), 2)
        self.assertAlmostEqual(perf["expectancy_r"], calc_exp, places=1)

    # ==========================================================
    # 10. HISTORICAL VS LIVE SEPARATION
    # ==========================================================
    def test_historical_vs_live_separation(self):
        """Strict Mandate: Never show LIVE if the provider is offline or unauthenticated."""
        dhan = DhanClient(client_id="", access_token="")
        self.assertFalse(dhan.is_authenticated)

        market_status = dhan.get_market_status("NIFTY")
        # Under no circumstances should NIFTY status be LIVE when credentials are absent
        self.assertNotEqual(market_status["status"], "LIVE")
        self.assertNotEqual(market_status["feed_status"], "LIVE")
        self.assertFalse(market_status["is_live_feed"])


if __name__ == "__main__":
    unittest.main()
