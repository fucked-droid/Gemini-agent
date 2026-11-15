"""
Unit Tests for FastAPI Web Terminal Endpoints.
Direct functional verification of route handlers, schemas, and static serving.
"""

import os
import unittest
import sys
from pathlib import Path

os.environ["TESTING"] = "1"

# Add live-market-terminal to path
TERMINAL_ROOT = Path(__file__).resolve().parent.parent
if str(TERMINAL_ROOT) not in sys.path:
    sys.path.insert(0, str(TERMINAL_ROOT))

from web_server import (
    serve_index,
    get_overview,
    get_candles,
    get_internals,
    get_decision,
    get_forecasts,
    get_options,
    get_performance,
    get_smc,
    get_orderflow,
    get_health,
)

class TestWebServer(unittest.TestCase):

    def test_serve_index(self):
        resp = serve_index()
        self.assertEqual(resp.status_code, 200)
        self.assertIn("INDIAN MARKET TERMINAL", resp.body.decode("utf-8"))

    def test_get_overview(self):
        data = get_overview()
        self.assertIsInstance(data, dict)
        self.assertIn("quotes", data)
        self.assertIn("market_status", data)
        self.assertIn("system_status", data)

    def test_get_candles(self):
        data = get_candles(symbol="NIFTY", timeframe="5m")
        self.assertEqual(data["symbol"], "NIFTY")
        self.assertIn("bars", data)
        self.assertGreater(data["count"], 0)
        first_bar = data["bars"][0]
        self.assertIn("close", first_bar)
        self.assertIn("volume", first_bar)
        self.assertIn("cvd", first_bar)

    def test_get_internals(self):
        data = get_internals(symbol="NIFTY")
        self.assertIsInstance(data, dict)

    def test_get_decision(self):
        data = get_decision(symbol="NIFTY")
        self.assertIsInstance(data, dict)

    def test_get_forecasts(self):
        data = get_forecasts(symbol="NIFTY")
        self.assertIsInstance(data, dict)

    def test_get_options(self):
        data = get_options(symbol="NIFTY")
        self.assertIsInstance(data, dict)
        self.assertIn("pcr_oi", data)
        self.assertIn("max_pain", data)
        self.assertIn("key_strikes", data)

        # BANKNIFTY test
        data_bn = get_options(symbol="BANKNIFTY")
        self.assertIsInstance(data_bn, dict)
        self.assertIn("pcr_oi", data_bn)

        # BTC crypto test (graceful unavailable)
        data_btc = get_options(symbol="BTC")
        self.assertEqual(data_btc.get("sentiment"), "Unavailable")

    def test_get_performance(self):
        data = get_performance(symbol="NIFTY")
        self.assertIsInstance(data, dict)
        self.assertIn("historical_accuracy_pct", data)
        self.assertIn("win_rate_pct", data)
        self.assertIn("profit_factor", data)

        # BANKNIFTY test
        data_bn = get_performance(symbol="BANKNIFTY")
        self.assertIsInstance(data_bn, dict)
        self.assertIn("max_drawdown_pts", data_bn)

    def test_get_smc(self):
        data = get_smc(symbol="NIFTY")
        self.assertIsInstance(data, dict)
        self.assertIn("has_smc_setup", data)

    def test_get_orderflow(self):
        data = get_orderflow(symbol="NIFTY")
        self.assertIsInstance(data, dict)
        self.assertIn("cvd", data)
        self.assertIn("volume_profile", data)
        self.assertIn("vwap_bands", data)

    def test_get_health(self):
        data = get_health()
        self.assertEqual(data["status"], "HEALTHY")
        self.assertIn("active_clients", data)

if __name__ == "__main__":
    unittest.main()
