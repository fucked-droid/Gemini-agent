"""
Unit Tests for Trading Decision Engine and Risk Manager.
Tests BUY, SELL, and WAIT signal generation, Stop-Loss / Target computations,
and risk-adjusted position sizing.
"""

import unittest

import sys
from pathlib import Path
TERMINAL_ROOT = Path(__file__).resolve().parent.parent
if str(TERMINAL_ROOT) not in sys.path:
    sys.path.insert(0, str(TERMINAL_ROOT))

from signals.decision_engine import TradingDecisionEngine
from signals.risk_management import RiskManager

class TestDecisionEngine(unittest.TestCase):

    def setUp(self):
        self.spot = 25000.0
        self.bullish_indicators = {
            "vwap": 24900.0,      # spot > vwap
            "ema10": 24980.0,     # ema10 > ema20
            "ema20": 24950.0,
            "rsi": 62.0,          # rsi > 54
            "macd_hist": 8.5,     # macd_hist > 0
            "atr": 100.0,
        }
        self.bullish_mtf = {
            "composite_trend": "BULLISH",
            "bullish_timeframes": 4,
            "bearish_timeframes": 0,
        }
        self.bullish_flow = {
            "order_flow_state": "STRONG_BULLISH_FLOW",
            "buyer_percentage": 62.0,
            "divergence": "NONE",
        }
        self.bullish_structure = {
            "structure_state": "BULLISH_EXPANSION",
        }
        self.bullish_breadth = {
            "breadth_score": 0.40,
            "advances": 38,
            "declines": 12,
        }

    def test_buy_signal_generation(self):
        res = TradingDecisionEngine.evaluate(
            spot_price=self.spot,
            indicators=self.bullish_indicators,
            mtf_data=self.bullish_mtf,
            order_flow=self.bullish_flow,
            market_structure=self.bullish_structure,
            market_breadth=self.bullish_breadth,
        )

        self.assertEqual(res["decision"], "BUY")
        self.assertGreaterEqual(res["confidence_pct"], 70.0)
        # In a BUY trade, Stop-Loss must be below spot price
        self.assertLess(res["stop_loss"], self.spot)
        # Targets must be above spot price
        self.assertGreater(res["target_1"], self.spot)
        self.assertGreater(res["target_2"], res["target_1"])
        self.assertTrue(len(res["invalidation_conditions"]) > 0)
        self.assertTrue(len(res["reasons"]) > 0)

    def test_sell_signal_generation(self):
        bearish_indicators = {
            "vwap": 25150.0,
            "ema10": 24920.0,
            "ema20": 24960.0,
            "rsi": 38.0,
            "macd_hist": -12.0,
            "atr": 100.0,
        }
        bearish_mtf = {"composite_trend": "BEARISH", "bullish_timeframes": 0, "bearish_timeframes": 4}
        bearish_flow = {"order_flow_state": "STRONG_BEARISH_FLOW", "buyer_percentage": 36.0, "divergence": "NONE"}
        bearish_struct = {"structure_state": "BEARISH_EXPANSION"}
        bearish_breadth = {"breadth_score": -0.50, "advances": 10, "declines": 40}

        # 1. Unconstrained Institutional Short Mode (buy_priority_mode=False)
        res_unconstrained = TradingDecisionEngine.evaluate(
            spot_price=self.spot,
            indicators=bearish_indicators,
            mtf_data=bearish_mtf,
            order_flow=bearish_flow,
            market_structure=bearish_struct,
            market_breadth=bearish_breadth,
            buy_priority_mode=False,
        )

        self.assertEqual(res_unconstrained["decision"], "SELL")
        self.assertGreaterEqual(res_unconstrained["confidence_pct"], 60.0)
        # In a SELL trade, Stop-Loss must be above spot price
        self.assertGreater(res_unconstrained["stop_loss"], self.spot)
        # Targets must be below spot price
        self.assertLess(res_unconstrained["target_1"], self.spot)
        self.assertLess(res_unconstrained["target_2"], res_unconstrained["target_1"])

        # 2. Buy-Priority / Low-Capital Protection Mode (buy_priority_mode=True)
        res_capital_shield = TradingDecisionEngine.evaluate(
            spot_price=self.spot,
            indicators=bearish_indicators,
            mtf_data=bearish_mtf,
            order_flow=bearish_flow,
            market_structure=bearish_struct,
            market_breadth=bearish_breadth,
            buy_priority_mode=True,
        )

        self.assertEqual(res_capital_shield["decision"], "AVOID_SHORT (CAPITAL_PRESERVATION)")
        self.assertEqual(res_capital_shield["capital_mode"], "BUY_PRIORITY_LOW_CAPITAL")
        self.assertIn("AVOID SHORT", res_capital_shield["signal_recommendation"])
        self.assertTrue(any("CAPITAL PROTECTION" in inv for inv in res_capital_shield["invalidation_conditions"]))

    def test_wait_signal_on_mixed_internals(self):
        mixed_mtf = {"composite_trend": "SIDEWAYS", "bullish_timeframes": 2, "bearish_timeframes": 2}
        mixed_flow = {"order_flow_state": "NEUTRAL_CHOP_FLOW", "buyer_percentage": 50.0, "divergence": "NONE"}
        mixed_indicators = {"vwap": self.spot, "ema10": self.spot, "ema20": self.spot, "rsi": 50.0, "macd_hist": 0.0, "atr": 50.0}

        res = TradingDecisionEngine.evaluate(
            spot_price=self.spot,
            indicators=mixed_indicators,
            mtf_data=mixed_mtf,
            order_flow=mixed_flow,
            market_structure={"structure_state": "NEUTRAL_CONSOLIDATION"},
            market_breadth={"breadth_score": 0.0, "advances": 25, "declines": 25},
        )

        self.assertEqual(res["decision"], "WAIT")
        self.assertEqual(res["confidence_pct"], 50.0)

    def test_risk_management_position_sizing(self):
        sizing = RiskManager.calculate_position_sizing(
            entry_price=25000.0,
            stop_loss_price=24920.0,  # 80 pts risk
            lot_size=25,              # NIFTY lot size
            account_size=500000.0,    # 5L account
            risk_pct=1.0,             # 1% = ₹5,000 max risk
        )

        # ₹5000 / (80 * 25 = ₹2000 per lot) = 2 lots
        self.assertEqual(sizing["recommended_lots"], 2)
        self.assertEqual(sizing["total_quantity"], 50)
        self.assertEqual(sizing["projected_risk_rupees"], 4000.0)

if __name__ == "__main__":
    unittest.main()
