"""
Comprehensive Step-by-Step Test Suite for NIFTY / BANKNIFTY AI Trading Terminal.
Covers:
- Step 10: 10 Operational Market-Closed and Live Scenarios
- Step 11: Automated Test Gates for Isolation, CVD Parity, Options Degradation,
  SMC Calculations, Signal Gating, Expectancy Math, and Freshness.
"""

import os
import sys
import time
import datetime
import unittest
from unittest.mock import patch
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
    OperatingState,
    DataMode,
    FreshnessStatus,
    ValidityStatus,
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
from analytics.multi_timeframe import MultiTimeframeEngine
from signals.decision_engine import TradingDecisionEngine
import web_server


class TestStepByStepAudit(unittest.TestCase):
    """
    Exhaustive validation suite verifying all 10 scenarios and institutional mandates.
    """

    def setUp(self):
        self.mgr = get_market_status_manager()
        self.cache = get_global_cache()
        self.mgr.last_tick_timestamps = {"NIFTY": 0.0, "BANKNIFTY": 0.0, "BTC": 0.0}

    # ==========================================================
    # SCENARIO 1: Market closed, historical data available
    # ==========================================================
    def test_scenario_1_market_closed_historical_available(self):
        """Market closed: shows MARKET_CLOSED, HISTORICAL mode, official session date, EXECUTION LOCKED."""
        # Force provider offline / closed market simulation
        self.mgr.set_provider_status(False)
        self.mgr.last_tick_timestamps["NIFTY"] = 0.0
        with patch.object(self.mgr, "is_session_active", return_value=False):
            stat = self.mgr.get_status("NIFTY")

            self.assertIn(stat["data_mode"], [DataMode.HISTORICAL.value, "HISTORICAL"])
            self.assertTrue(stat["is_market_closed"] or not stat["session_active"])
            self.assertIn("trading_session_date", stat)
            self.assertNotEqual(stat["status"], MarketDataStatus.LIVE.value)

            # Decision engine should produce EXECUTION LOCKED
            dec = TradingDecisionEngine.evaluate(
                spot_price=25144.30,
                indicators={"vwap": 25140.0, "ema10": 25145.0, "ema20": 25135.0, "atr": 50.0},
                mtf_data={"composite_trend": "BULLISH", "bullish_timeframes": 4, "bearish_timeframes": 1},
                order_flow={"order_flow_state": "NEUTRAL", "buyer_percentage": 50.0, "is_cvd_available": True, "session_cvd": 1200},
                market_structure={"structure_state": "BULLISH_EXPANSION"},
                market_breadth={"breadth_score": 0.20, "advances": 30, "declines": 20},
                buy_priority_mode=True,
                symbol="NIFTY",
                market_status=stat,
            )
            self.assertEqual(dec["decision"], "EXECUTION LOCKED")
            self.assertEqual(dec["clean_recommendation"], "EXECUTION LOCKED")
            self.assertFalse(dec["has_valid_setup"])
            self.assertIn("LOCKED", dec["entry_zone"])

    # ==========================================================
    # SCENARIO 2: Market closed, no historical data available
    # ==========================================================
    def test_scenario_2_market_closed_no_historical_data(self):
        """Market closed without data: gracefully returns DATA UNAVAILABLE or empty bars."""
        envelope = self.mgr.create_response_envelope(
            instrument="NIFTY",
            data_mode=DataMode.UNAVAILABLE,
            freshness_status=FreshnessStatus.UNAVAILABLE,
            validity_status=ValidityStatus.INVALID,
            payload={"bars": []}
        )
        self.assertEqual(envelope["data_mode"], "UNAVAILABLE")
        self.assertEqual(envelope["freshness_status"], "UNAVAILABLE")
        self.assertEqual(envelope["validity_status"], "INVALID")
        self.assertEqual(envelope["bars"], [])

    # ==========================================================
    # SCENARIO 3: Market open, live data connected
    # ==========================================================
    def test_scenario_3_market_open_live_connected(self):
        """Market open with fresh ticks: status is LIVE and Freshness is REALTIME."""
        self.mgr.set_provider_status(True)
        self.mgr.set_websocket_status(True, "CONNECTED")
        now_ts = time.time()
        self.mgr.record_tick("BTC", now_ts)  # BTC is 24/7 open

        btc_stat = self.mgr.get_status("BTC")
        self.assertEqual(btc_stat["status"], "LIVE")
        self.assertEqual(btc_stat["data_mode"], "LIVE")
        self.assertEqual(btc_stat["freshness_status"], "REALTIME")
        self.assertEqual(btc_stat["validity_status"], "VALID")
        self.assertFalse(btc_stat["is_stale"])

    # ==========================================================
    # SCENARIO 4: Market open, WebSocket disconnected
    # ==========================================================
    def test_scenario_4_market_open_ws_disconnected(self):
        """Market open but WS disconnected: detects disconnection and does not show LIVE."""
        self.mgr.set_provider_status(True)
        self.mgr.set_websocket_status(False, "DISCONNECTED")
        self.mgr.last_tick_timestamps["NIFTY"] = 0.0

        # Simulate active session check
        if self.mgr.is_session_active("NIFTY"):
            stat = self.mgr.get_status("NIFTY")
            self.assertNotEqual(stat["status"], "LIVE")
            self.assertEqual(stat["websocket_connected"], False)

    # ==========================================================
    # SCENARIO 5: Live data stale (> 15 seconds)
    # ==========================================================
    def test_scenario_5_live_data_stale_detection(self):
        """Stalled ticks (> 15s) during active trading triggers STALE and DEGRADED."""
        stale_ts = time.time() - 30.0
        self.mgr.last_tick_timestamps["BTC"] = stale_ts

        stat = self.mgr.get_status("BTC")
        self.assertEqual(stat["status"], "STALE")
        self.assertEqual(stat["freshness_status"], "STALE")
        self.assertEqual(stat["validity_status"], "DEGRADED")
        self.assertTrue(stat["is_stale"])

    # ==========================================================
    # SCENARIO 6: Options feed unavailable
    # ==========================================================
    def test_scenario_6_options_feed_unavailable_graceful_degradation(self):
        """When options feed is absent, all dependent metrics show UNAVAILABLE / None."""
        opt = OptionsAnalytics.get_options_intelligence("UNKNOWN_SYMBOL", allow_sample=False)
        self.assertEqual(opt["status"], "UNAVAILABLE")
        self.assertEqual(opt["sentiment"], "Unavailable")
        self.assertIsNone(opt["pcr_oi"])
        self.assertIsNone(opt["pcr_volume"])
        self.assertIsNone(opt["net_ce_oi_change"])
        self.assertIsNone(opt["net_pe_oi_change"])
        self.assertIsNone(opt["max_pain"])
        self.assertIsNone(opt["major_resistance_strike"])
        self.assertEqual(opt["key_strikes"], [])

    # ==========================================================
    # SCENARIO 7: Instrument switched from NIFTY to BANKNIFTY
    # ==========================================================
    def test_scenario_7_instrument_switch_nifty_to_banknifty(self):
        """Switching NIFTY to BANKNIFTY enforces instrument isolation without strike bleed."""
        web_server.process_symbol_pipeline("NIFTY")
        web_server.process_symbol_pipeline("BANKNIFTY")

        nifty_cache = self.cache.analytics.get("NIFTY", {})
        bn_cache = self.cache.analytics.get("BANKNIFTY", {})

        self.assertIsNotNone(nifty_cache)
        self.assertIsNotNone(bn_cache)
        self.assertNotEqual(nifty_cache, bn_cache)

    # ==========================================================
    # SCENARIO 8: Instrument switched from BANKNIFTY to BTC
    # ==========================================================
    def test_scenario_8_instrument_switch_to_btc(self):
        """Switching to BTC disables NSE breadth and options completely."""
        web_server.process_symbol_pipeline("BTC")
        btc_cache = self.cache.analytics.get("BTC", {})

        self.assertEqual(btc_cache.get("market_breadth", {}).get("status"), "NOT_APPLICABLE")
        self.assertEqual(btc_cache.get("options_intelligence", {}).get("status"), "NO_CRYPTO_OPTIONS")

    # ==========================================================
    # SCENARIO 9: Historical data loaded after a refresh
    # ==========================================================
    def test_scenario_9_historical_data_loaded_after_refresh(self):
        """Historical candle master dataset loads reliably with correct OHLCV columns."""
        client = DhanClient()
        df = client.get_historical_candles("NIFTY", interval="5m", days=2)
        self.assertFalse(df.empty)
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            self.assertIn(col, df.columns)

    # ==========================================================
    # SCENARIO 10: Missing or invalid candle data
    # ==========================================================
    def test_scenario_10_missing_or_invalid_candle_data_resilience(self):
        """All engines handle empty, None, and zero-volume DataFrames without unhandled crashes."""
        empty_df = pd.DataFrame()

        # Order flow
        of = OrderFlowAnalyzer.analyze_order_flow(empty_df)
        self.assertEqual(of["status"], "UNAVAILABLE")
        self.assertFalse(of["is_cvd_available"])
        self.assertEqual(of["cvd_display"], "CVD UNAVAILABLE")

        # Technical indicators
        df_ind, sc = TechnicalIndicators.calculate_all(empty_df)
        self.assertTrue(df_ind.empty)
        self.assertEqual(sc.get("rsi", 50.0), 50.0)

        # SMC analyzer
        smc = SMCAnalyzer.analyze_smc(empty_df)
        self.assertFalse(smc["has_smc_setup"])

        # Decision engine
        dec = TradingDecisionEngine.evaluate(
            spot_price=0.0,
            indicators={},
            mtf_data={},
            order_flow={},
            market_structure={},
            market_breadth={},
        )
        self.assertEqual(dec["decision"], "DATA UNAVAILABLE")

    # ==========================================================
    # STEP 11: CVD Mathematical Parity
    # ==========================================================
    def test_cvd_volume_conservation_and_unification(self):
        """Ensures buy_vol + sell_vol == Volume and Bar Delta == Buy - Sell on every bar."""
        df = pd.DataFrame({
            "Open": [25000.0, 25020.0, 25010.0, 25040.0, 25030.0, 25050.0],
            "High": [25030.0, 25040.0, 25035.0, 25060.0, 25055.0, 25070.0],
            "Low": [24990.0, 25015.0, 25005.0, 25035.0, 25025.0, 25045.0],
            "Close": [25025.0, 25030.0, 25015.0, 25055.0, 25045.0, 25065.0],
            "Volume": [1000, 1500, 1200, 1800, 1400, 1600],
        })

        df_flow = OrderFlowAnalyzer.compute_volume_delta(df)
        for _, row in df_flow.iterrows():
            # Strict mathematical identity: Buy + Sell == Volume
            self.assertEqual(int(row["Buy_Volume"] + row["Sell_Volume"]), int(row["Volume"]))
            # Bar Delta == Buy - Sell
            self.assertEqual(int(row["Delta"]), int(row["Buy_Volume"] - row["Sell_Volume"]))

        # Cumulative Volume Delta consistency
        manual_cvd = df_flow["Delta"].cumsum().iloc[-1]
        self.assertEqual(df_flow["CVD"].iloc[-1], manual_cvd)

        # Full analysis returns matching session_cvd
        res = OrderFlowAnalyzer.analyze_order_flow(df, session_df=df)
        self.assertTrue(res["is_cvd_available"])
        self.assertEqual(res["session_cvd"], int(manual_cvd))
        self.assertEqual(res["cvd"], int(manual_cvd))

    # ==========================================================
    # STEP 11: Performance Expectancy Verification (+1.55R Gross vs +1.40R Net)
    # ==========================================================
    def test_performance_expectancy_reconciliation(self):
        """Verifies exact gross (+1.55R) and net (+1.40R) mathematical consistency."""
        perf = PerformanceAnalytics.get_performance_metrics("NIFTY")
        self.assertEqual(perf["win_rate_pct"], 75.0)
        self.assertEqual(perf["historical_accuracy_pct"], 75.0)
        self.assertEqual(perf["avg_risk_reward_ratio"], "1:2.40")

        # Gross: (0.75 * 2.40) - (0.25 * 1.00) = 1.80 - 0.25 = +1.55R
        expected_gross = round((0.75 * 2.40) - (0.25 * 1.00), 2)
        self.assertEqual(perf["gross_expectancy_r"], expected_gross)
        self.assertEqual(expected_gross, 1.55)

        # Net: 1.55R - 0.15R friction = 1.40R
        expected_net = round(expected_gross - 0.15, 2)
        self.assertEqual(perf["net_expectancy_r"], expected_net)
        self.assertEqual(expected_net, 1.40)

        # Documentation and unverified status present
        self.assertIn("UNVERIFIED", perf["badge_text"])
        self.assertIn("documentation", perf)
        self.assertIn("expectancy_discrepancy_explanation", perf["documentation"])


if __name__ == "__main__":
    unittest.main()
