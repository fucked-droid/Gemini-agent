"""
Unit and Integration Tests for Trading Intelligence and Critical Feed Upgrades.
Validates:
1. Multi-Timeframe Analysis (5m, 15m, 1h, daily 4-Tier Institutional Confluence)
2. Option Greeks, ATM IV, IV Skew, and Exchange Parity Verification
3. Market Regime Detection (Trending, Sideways, Volatile, ADX, Choppiness Index)
4. News & Event Risk Detection (Sentiment Scoring, Calendar Risks, Haircut)
5. Decision Engine Mathematical Geometry (SL < Entry < T1 < T2, None on WAIT)
6. REST API Endpoints (/api/regime, /api/news, /api/greeks, /api/mtf)
"""

import os
os.environ["TESTING"] = "1"

import sys
import unittest
from pathlib import Path

TERMINAL_ROOT = Path(__file__).resolve().parent.parent
if str(TERMINAL_ROOT) not in sys.path:
    sys.path.insert(0, str(TERMINAL_ROOT))

import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

from data import DhanClient, get_market_status_manager
from analytics import (
    MultiTimeframeEngine,
    OptionsAnalytics,
    MarketRegimeDetector,
    NewsAndEventRiskEngine,
    TechnicalIndicators,
)
from signals import TradingDecisionEngine
from web_server import (
    get_market_regime,
    get_news_and_events,
    get_option_greeks,
    get_multi_timeframe,
)


class TestTradingIntelligence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Generate synthetic realistic OHLCV candles
        np.random.seed(42)
        n = 100
        dates = pd.date_range("2026-11-15 09:15", periods=n, freq="5min")
        close = 25000.0 + np.cumsum(np.random.randn(n) * 15.0)
        high = close + np.random.rand(n) * 10.0
        low = close - np.random.rand(n) * 10.0
        open_p = low + np.random.rand(n) * (high - low)
        volume = np.random.randint(1000, 25000, size=n)

        cls.df_5m = pd.DataFrame({
            "Open": open_p,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        }, index=dates)

        # Generate daily candles for macro timeframe
        daily_dates = pd.date_range("2026-08-01", periods=60, freq="B")
        d_close = 24000.0 + np.cumsum(np.random.randn(60) * 50.0)
        d_high = d_close + np.random.rand(60) * 60.0
        d_low = d_close - np.random.rand(60) * 60.0
        d_open = d_low + np.random.rand(60) * (d_high - d_low)
        d_volume = np.random.randint(50000, 200000, size=60)

        cls.df_daily = pd.DataFrame({
            "Open": d_open,
            "High": d_high,
            "Low": d_low,
            "Close": d_close,
            "Volume": d_volume,
        }, index=daily_dates)

    # 1. Multi-Timeframe Analysis Tests
    def test_institutional_4tf_confluence(self):
        tf_suite = {
            "5m": self.df_5m,
            "15m": self.df_5m.iloc[::3],
            "1h": self.df_5m.iloc[::12],
            "daily": self.df_daily,
        }
        res = MultiTimeframeEngine.institutional_4tf(tf_suite, spot_price=25150.0)
        
        self.assertIn("confluence_state", res)
        self.assertIn("tactical_5m", res)
        self.assertIn("intraday_swing_15m", res)
        self.assertIn("session_bias_1h", res)
        self.assertIn("macro_regime_daily", res)
        self.assertIn("aligned_score", res)
        self.assertIn("execution_bias", res)
        self.assertIsInstance(res["aligned_score"], int)
        self.assertTrue(-4 <= res["aligned_score"] <= 4)

    # 2. Market Regime Detection Tests
    def test_market_regime_detector_trending_and_sideways(self):
        # Test default synthetic df
        regime = MarketRegimeDetector.detect_regime(self.df_5m, india_vix=15.5, symbol="NIFTY")
        self.assertIn("regime", regime)
        self.assertIn("adx", regime)
        self.assertIn("chop_index", regime)
        self.assertIn("bb_bandwidth", regime)
        self.assertIn("actionable_strategy", regime)
        self.assertIn("regime_explanation", regime)
        self.assertTrue(0 <= regime["chop_index"] <= 100)
        self.assertTrue(regime["adx"] >= 0)

        # Test strong trend synthetic df
        trending_df = self.df_5m.copy()
        trending_df["Close"] = 25000.0 + np.arange(len(trending_df)) * 20.0  # strong upward drift
        trending_df["High"] = trending_df["Close"] + 5.0
        trending_df["Low"] = trending_df["Close"] - 5.0
        trending_regime = MarketRegimeDetector.detect_regime(trending_df, india_vix=14.0, symbol="NIFTY")
        self.assertIn("BULLISH", trending_regime["regime"])
        self.assertGreaterEqual(trending_regime["adx"], 25.0)

    # 3. Option Greeks & Exchange Parity Tests
    def test_option_greeks_and_iv(self):
        opt = OptionsAnalytics.get_options_intelligence("NIFTY", spot_price=24530.0, allow_sample=True)
        self.assertIn("atm_greeks", opt)
        self.assertIn("atm_iv", opt)
        self.assertIn("iv_skew", opt)
        self.assertIn("exchange_verification", opt)

        greeks = opt["atm_greeks"]
        self.assertIn("delta_call", greeks)
        self.assertIn("delta_put", greeks)
        self.assertIn("gamma", greeks)
        self.assertIn("theta_call", greeks)
        self.assertIn("vega", greeks)

        # Greeks mathematical invariants
        self.assertTrue(0.0 <= greeks["delta_call"] <= 1.0)
        self.assertTrue(-1.0 <= greeks["delta_put"] <= 0.0)
        self.assertTrue(greeks["gamma"] >= 0.0)
        self.assertTrue(greeks["vega"] >= 0.0)

        # Exchange verification invariants
        ex_ver = opt["exchange_verification"]
        self.assertIn(ex_ver["status"], ["VERIFIED_EXCHANGE", "VERIFIED_SNAPSHOT", "UNVERIFIED_PRICE_DEVIATION"])

    # 4. News and Macro Event Risk Tests
    def test_news_and_event_risk_engine(self):
        news = NewsAndEventRiskEngine.get_market_news_and_events()
        self.assertIn("market_sentiment_score", news)
        self.assertIn("market_sentiment_label", news)
        self.assertIn("event_risk_level", news)
        self.assertIn("position_sizing_multiplier", news)
        self.assertIn("headlines", news)
        self.assertIn("calendar_events", news)

        # Invariants
        self.assertTrue(-1.0 <= news["market_sentiment_score"] <= 1.0)
        self.assertIn(news["event_risk_level"], ["LOW", "MODERATE", "HIGH"])
        self.assertTrue(0.3 <= news["position_sizing_multiplier"] <= 1.0)

    # 5. Trading Decision Mathematical Invariants
    def test_decision_engine_mathematical_geometry(self):
        status_mgr = get_market_status_manager()
        open_status = {
            "is_market_open": True,
            "session_phase": "REGULAR_SESSION",
            "data_mode": "LIVE_FEED",
            "is_stale": False,
        }

        # BUY Setup
        indicators_bull = {
            "rsi": 58.0,
            "vwap": 25100.0,
            "ema10": 25120.0,
            "ema20": 25105.0,
            "atr": 45.0,
        }
        order_flow_bull = {
            "buyer_percentage": 62.0,
            "seller_percentage": 38.0,
            "order_flow_state": "STRONG_BUYING",
            "cvd": 12000,
            "divergence": "BULLISH_ABSORPTION",
            "is_cvd_available": True,
        }
        mtf_bull = {
            "composite_trend": "BULLISH",
            "timeframes": {
                "5m": {"direction": "BULLISH"},
                "15m": {"direction": "BULLISH"},
                "1h": {"direction": "BULLISH"},
            }
        }
        structure_bull = {
            "structure_state": "BULLISH_EXPANSION",
            "nearest_support": 25050.0,
            "nearest_resistance": 25250.0,
        }
        smc_bull = {
            "setup_type": "ORDER_BLOCK_PULLBACK",
            "has_valid_setup": True,
            "bullish_entry": 25120.0,
            "bullish_sl": 25060.0,
            "bullish_t1": 25240.0,
            "bullish_t2": 25340.0,
            "reversal_risk": {"risk_level": "LOW", "chance_pct": 20.0},
        }

        dec_buy = TradingDecisionEngine.evaluate(
            spot_price=25130.0,
            indicators=indicators_bull,
            mtf_data=mtf_bull,
            order_flow=order_flow_bull,
            market_structure=structure_bull,
            market_breadth={"adr": 1.8, "advances": 35, "declines": 15},
            smc_data=smc_bull,
            symbol="NIFTY",
            market_status=open_status,
            data_mode="LIVE_FEED",
            is_stale=False,
        )

        if dec_buy["decision"] == "BUY":
            sl = dec_buy["stop_loss"]
            entry = dec_buy["fixed_entry_price"]
            t1 = dec_buy["target_1"]
            t2 = dec_buy["target_2"]
            self.assertIsNotNone(sl)
            self.assertIsNotNone(t1)
            self.assertIsNotNone(t2)
            # Mathematical geometry check for Long: SL < Entry < T1 < T2
            self.assertLess(sl, entry, "Stop loss must be strictly below entry for BUY")
            self.assertLess(entry, t1, "Target 1 must be strictly above entry for BUY")
            self.assertLess(t1, t2, "Target 2 must be strictly above Target 1 for BUY")

        # WAIT Setup: Stop loss, Target 1, and Target 2 must be None (no fake placeholder levels)
        dec_wait = TradingDecisionEngine.evaluate(
            spot_price=25130.0,
            indicators=indicators_bull,
            mtf_data={"composite_trend": "SIDEWAYS"},
            order_flow={"buyer_percentage": 50.0, "order_flow_state": "BALANCED"},
            market_structure={"structure_state": "SIDEWAYS_RANGE"},
            market_breadth={"adr": 1.0, "advances": 25, "declines": 25},
            smc_data={"has_valid_setup": False},
            symbol="NIFTY",
            market_status={"is_market_open": False, "session_phase": "WEEKEND", "data_mode": "HISTORICAL"},
            data_mode="HISTORICAL",
            is_stale=False,
        )
        self.assertIn(dec_wait["decision"], ["WAIT", "EXECUTION LOCKED"])
        self.assertIsNone(dec_wait["stop_loss"], "Stop loss must be None in non-active mode")
        self.assertIsNone(dec_wait["target_1"], "Target 1 must be None in non-active mode")
        self.assertIsNone(dec_wait["target_2"], "Target 2 must be None in non-active mode")

    # 6. REST API Endpoints Tests
    def test_rest_api_regime_and_news_endpoints(self):
        # /api/regime
        data_regime = get_market_regime(symbol="NIFTY")
        self.assertIn("regime", data_regime)
        self.assertIn("adx", data_regime)
        self.assertIn("last_updated_timestamp", data_regime)
        self.assertIn("data_source", data_regime)

        # /api/news
        data_news = get_news_and_events()
        self.assertIn("event_risk_level", data_news)
        self.assertIn("headlines", data_news)
        self.assertIn("last_updated_timestamp", data_news)

        # /api/greeks
        data_greeks = get_option_greeks(symbol="NIFTY")
        self.assertIn("atm_greeks", data_greeks)
        self.assertIn("atm_iv", data_greeks)
        self.assertIn("exchange_verification", data_greeks)
        self.assertIn("last_updated_timestamp", data_greeks)

        # /api/mtf
        data_mtf = get_multi_timeframe(symbol="NIFTY")
        self.assertIn("institutional_4tf", data_mtf)
        self.assertIn("last_updated_timestamp", data_mtf)


if __name__ == "__main__":
    unittest.main()
