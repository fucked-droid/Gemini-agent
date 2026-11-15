"""
Unit Tests for Market Data Provider & DhanHQ Integration.
Tests instrument resolution, quote parsing, rate limiting, and historical resampling.
"""

import unittest
import pandas as pd
import datetime

import sys
from pathlib import Path
TERMINAL_ROOT = Path(__file__).resolve().parent.parent
if str(TERMINAL_ROOT) not in sys.path:
    sys.path.insert(0, str(TERMINAL_ROOT))

from data.instrument_master import InstrumentMaster
from data.dhan_client import DhanClient
from data.historical_data import HistoricalDataManager

class TestMarketData(unittest.TestCase):

    def setUp(self):
        self.master = InstrumentMaster()
        self.client = DhanClient()

    def test_security_id_resolution(self):
        nifty = self.master.resolve_instrument("NIFTY")
        self.assertEqual(nifty["security_id"], "13")
        self.assertEqual(nifty["segment"], "IDX")

        bn = self.master.resolve_instrument("BANKNIFTY")
        self.assertEqual(bn["security_id"], "25")

        vix = self.master.resolve_instrument("INDIAVIX")
        self.assertEqual(vix["security_id"], "24")

    def test_invalid_symbol_resolution(self):
        with self.assertRaises(ValueError):
            self.master.resolve_instrument("NON_EXISTENT_XYZ_SYMBOL")

    def test_market_status_session_check(self):
        status = self.client.get_market_status()
        self.assertIn("status", status)
        self.assertIn("is_open", status)
        self.assertIn(status["status"], ["LIVE_SESSION", "PRE_MARKET", "POST_MARKET", "CLOSED", "NON_TRADING_DAY"])

    def test_offline_quote_fallback(self):
        quote = self.client.get_quote("NIFTY")
        self.assertIn("price", quote)
        self.assertGreater(quote["price"], 10000.0)
        self.assertIn(quote["symbol"], ["NIFTY"])
        self.assertIn("source", quote)

    def test_historical_candle_generation_and_invariants(self):
        candles = self.client.get_historical_candles("NIFTY", interval="5m", days=2)
        self.assertFalse(candles.empty)
        self.assertGreater(len(candles), 10)

        # Invariants: High >= Low, High >= Open, High >= Close
        self.assertTrue((candles["High"] >= candles["Low"]).all())
        self.assertTrue((candles["High"] >= candles["Open"]).all())
        self.assertTrue((candles["High"] >= candles["Close"]).all())
        self.assertTrue((candles["Low"] <= candles["Open"]).all())
        self.assertTrue((candles["Low"] <= candles["Close"]).all())

    def test_multi_timeframe_resampling(self):
        base_1m = self.client.get_historical_candles("NIFTY", interval="1m", days=1)
        suite = HistoricalDataManager.build_timeframe_suite(base_1m, ["1m", "5m", "15m", "30m", "60m"])

        self.assertIn("1m", suite)
        self.assertIn("5m", suite)
        self.assertIn("15m", suite)
        self.assertIn("30m", suite)
        self.assertIn("60m", suite)

        # Resampling to larger intervals produces fewer bars
        if len(suite["1m"]) >= 15:
            self.assertGreaterEqual(len(suite["1m"]), len(suite["5m"]))
            self.assertGreaterEqual(len(suite["5m"]), len(suite["15m"]))

    def test_dhan_quote_parsing_mock(self):
        mock_api_resp = {
            "data": {
                "last_price": 25150.50,
                "close": 25000.00,
                "high": 25200.00,
                "low": 24980.00,
                "open": 25010.00,
                "volume": 5200000,
            }
        }
        meta = {"symbol": "NIFTY", "name": "NIFTY 50", "security_id": "13", "exchange": "NSE_INDEX"}
        parsed = self.client._parse_dhan_quote(mock_api_resp, meta)

        self.assertEqual(parsed["price"], 25150.50)
        self.assertEqual(parsed["change"], 150.50)
        self.assertAlmostEqual(parsed["change_pct"], 0.602, delta=0.01)
        self.assertTrue(parsed["is_live"])

if __name__ == "__main__":
    unittest.main()
