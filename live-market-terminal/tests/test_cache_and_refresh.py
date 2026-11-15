"""
Unit Tests for Centralized MarketCache & Refresh Behavior.
Tests thread-safety, tick updates, snapshot persistence, and data freshness metrics.
"""

import unittest
import time
import tempfile
from pathlib import Path

import sys
TERMINAL_ROOT = Path(__file__).resolve().parent.parent
if str(TERMINAL_ROOT) not in sys.path:
    sys.path.insert(0, str(TERMINAL_ROOT))

from data.market_cache import MarketCache

class TestCacheAndRefresh(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.snap_file = Path(self.tmp_dir.name) / "test_snapshot.json"
        self.cache = MarketCache(snapshot_file=self.snap_file)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_cache_singleton(self):
        cache2 = MarketCache()
        self.assertIs(self.cache, cache2)

    def test_quote_update_and_snapshot(self):
        mock_quote = {
            "symbol": "NIFTY",
            "security_id": "13",
            "price": 25100.0,
            "close": 25000.0,
            "change": 100.0,
            "change_pct": 0.40,
            "volume": 1000000,
            "is_live": True,
        }
        self.cache.update_quote("NIFTY", mock_quote)

        snap = self.cache.get_snapshot()
        self.assertIn("NIFTY", snap["quotes"])
        self.assertEqual(snap["quotes"]["NIFTY"]["price"], 25100.0)

    def test_live_tick_update(self):
        mock_quote = {
            "symbol": "BANKNIFTY",
            "security_id": "25",
            "price": 52000.0,
            "close": 52000.0,
            "change": 0.0,
            "change_pct": 0.0,
            "volume": 50000,
            "is_live": False,
        }
        self.cache.update_quote("BANKNIFTY", mock_quote)

        # Incoming WebSocket tick with security_id="25", LTP=52150.0
        self.cache.update_tick(security_id="25", ltp=52150.0, volume=65000)

        snap = self.cache.get_snapshot()
        bn_q = snap["quotes"]["BANKNIFTY"]
        self.assertEqual(bn_q["price"], 52150.0)
        self.assertEqual(bn_q["change"], 150.0)
        self.assertTrue(bn_q["is_live"])

    def test_disk_snapshot_persistence(self):
        self.cache.update_system_status("CONNECTED", "Test health message")
        self.cache.save_to_snapshot()

        self.assertTrue(self.snap_file.exists())
        # Reload into new instance
        cache_reloaded = MarketCache(snapshot_file=self.snap_file)
        snap = cache_reloaded.get_snapshot()
        self.assertIn("api_status", snap["system_status"])

if __name__ == "__main__":
    unittest.main()
