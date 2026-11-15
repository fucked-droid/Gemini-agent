"""
Thread-safe Centralized Market Cache.
Stores quotes, candles, analytics, and signals shared seamlessly across
the CLI terminal, Streamlit dashboard, and background workers.
"""

import time
import json
import threading
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import pandas as pd

from config import (
    MARKET_STATE_SNAPSHOT_FILE,
    DEFAULT_REFRESH_INTERVAL_SECONDS,
)
from .market_status_manager import get_market_status_manager

logger = logging.getLogger("MarketCache")

class MarketCache:
    """
    Centralized in-memory and disk-synchronized state store.
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(MarketCache, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, snapshot_file: Optional[Path] = None):
        if snapshot_file is not None:
            self.snapshot_file = snapshot_file

        if getattr(self, "_initialized", False):
            return

        self.snapshot_file = snapshot_file or MARKET_STATE_SNAPSHOT_FILE
        self.lock = threading.RLock()

        self.quotes: Dict[str, Dict[str, Any]] = {}
        self.candles: Dict[str, Dict[str, pd.DataFrame]] = {}
        self.analytics: Dict[str, Dict[str, Any]] = {}
        self.signals: Dict[str, Dict[str, Any]] = {}
        self.forecasts: Dict[str, Dict[str, Any]] = {}
        self.market_status: Dict[str, Any] = {"status": "UNKNOWN", "is_open": False}

        self.system_status = {
            "api_status": "INITIALIZING",
            "message": "Starting engine...",
            "last_refresh_timestamp": 0.0,
            "next_refresh_seconds": DEFAULT_REFRESH_INTERVAL_SECONDS,
            "refresh_interval": DEFAULT_REFRESH_INTERVAL_SECONDS,
            "data_freshness_seconds": 0.0,
        }

        self._initialized = True
        self._load_from_snapshot()

    def update_quote(self, symbol: str, quote: Dict[str, Any]):
        """Updates quote for an instrument."""
        with self.lock:
            sym_upper = symbol.upper()
            self.quotes[sym_upper] = quote
            self.system_status["last_refresh_timestamp"] = time.time()
            if quote.get("is_live", False):
                get_market_status_manager().record_tick(sym_upper)

    def update_tick(self, security_id: str, ltp: float, volume: int = 0):
        """Processes live WebSocket tick."""
        with self.lock:
            for sym, q in self.quotes.items():
                if str(q.get("security_id")) == str(security_id):
                    prev = q.get("close", ltp)
                    q["price"] = ltp
                    q["change"] = round(ltp - prev, 2)
                    q["change_pct"] = round(((ltp - prev) / prev) * 100.0, 2) if prev != 0 else 0.0
                    q["volume"] = volume or q.get("volume", 0)
                    q["is_live"] = True
                    q["last_tick_time"] = time.time()
                    get_market_status_manager().record_tick(sym)
                    break

    def set_candles(self, symbol: str, tf_suite: Dict[str, pd.DataFrame]):
        """Sets multi-timeframe candles dictionary for an instrument."""
        with self.lock:
            self.candles[symbol.upper()] = tf_suite

    def get_candles(self, symbol: str, tf: str = "5m") -> Optional[pd.DataFrame]:
        """Retrieves candles for symbol and timeframe."""
        with self.lock:
            suite = self.candles.get(symbol.upper(), {})
            return suite.get(tf.lower())

    def update_analytics(self, symbol: str, data: Dict[str, Any]):
        """Updates technical indicators and structure."""
        with self.lock:
            self.analytics[symbol.upper()] = data

    def update_signals(self, symbol: str, data: Dict[str, Any]):
        """Updates BUY/SELL/WAIT decisions."""
        with self.lock:
            self.signals[symbol.upper()] = data

    def update_forecasts(self, symbol: str, data: Dict[str, Any]):
        """Updates multi-horizon forecasts."""
        with self.lock:
            self.forecasts[symbol.upper()] = data

    def update_market_status(self, status: Dict[str, Any]):
        """Updates market session status."""
        with self.lock:
            self.market_status = status

    def update_system_status(self, api_status: str, message: str = ""):
        """Updates overall system status."""
        with self.lock:
            self.system_status["api_status"] = api_status
            if message:
                self.system_status["message"] = message

    def get_snapshot(self) -> Dict[str, Any]:
        """Returns deep snapshot dictionary of current market state."""
        with self.lock:
            now = time.time()
            last_ts = self.system_status.get("last_refresh_timestamp", 0.0)
            freshness = round(now - last_ts, 1) if last_ts > 0 else 999.0

            # Convert non-serializable objects for snapshot
            return {
                "quotes": self.quotes,
                "analytics": self.analytics,
                "signals": self.signals,
                "forecasts": self.forecasts,
                "market_status": self.market_status,
                "system_status": {
                    **self.system_status,
                    "data_freshness_seconds": freshness,
                    "current_timestamp": time.strftime("%Y-%m-%d %H:%M:%S IST"),
                },
            }

    def save_to_snapshot(self):
        """Serializes current snapshot to disk for cross-process synchronization."""
        with self.lock:
            try:
                snap = self.get_snapshot()
                self.snapshot_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.snapshot_file, "w", encoding="utf-8") as f:
                    json.dump(snap, f, indent=2, default=str)
            except Exception as e:
                logger.debug(f"Failed to save snapshot: {e}")

    def _load_from_snapshot(self):
        """Loads cached snapshot on cold startup."""
        if self.snapshot_file.exists():
            try:
                with open(self.snapshot_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.quotes = data.get("quotes", {})
                    self.analytics = data.get("analytics", {})
                    self.signals = data.get("signals", {})
                    self.forecasts = data.get("forecasts", {})
                    self.market_status = data.get("market_status", {})
                    logger.info("Initialized MarketCache from persisted snapshot file.")
            except Exception as e:
                logger.warning(f"Could not load snapshot: {e}")

def get_global_cache() -> MarketCache:
    """Convenience getter for singleton MarketCache."""
    return MarketCache()
