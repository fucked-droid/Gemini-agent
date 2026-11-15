"""
Centralized Market Data Status & Quality Manager.
Single source of truth for market data feed status across all instruments.
Supported statuses:
  - LIVE: Active live market feed with ticks arriving in real-time.
  - HISTORICAL: Feed derived from historical candle master data (offline mode).
  - DELAYED: Feed delayed by exchange provider (> 1 minute).
  - OFFLINE: Data provider unreachable and no ticks arriving.
  - RECONNECTING: WebSocket or socket connection lost and attempting reconnect.
  - STALE: Market session is live, but no ticks received for > 15 seconds.
"""

import time
import datetime
import logging
from enum import Enum
from typing import Dict, Any, Optional

from config import SESSION_TIMINGS

logger = logging.getLogger("MarketStatusManager")


class MarketDataStatus(str, Enum):
    LIVE = "LIVE"
    HISTORICAL = "HISTORICAL"
    DELAYED = "DELAYED"
    OFFLINE = "OFFLINE"
    RECONNECTING = "RECONNECTING"
    STALE = "STALE"


class MarketStatusManager:
    """
    Centralized Authority for Feed Quality, Tick Freshness, and Data Source Tracking.
    Prevents false 'LIVE' indicators when providers are offline or ticks stop arriving.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MarketStatusManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self.last_tick_timestamps: Dict[str, float] = {
            "NIFTY": 0.0,
            "BANKNIFTY": 0.0,
            "BTC": 0.0,
        }
        self.provider_connected: bool = False
        self.provider_name: str = "DhanHQ Official v2 API"
        self.websocket_connected: bool = False
        self.websocket_state: str = "DISCONNECTED"  # CONNECTED, CONNECTING, DISCONNECTED, RECONNECTING
        self.subscription_status: Dict[str, bool] = {
            "NIFTY": False,
            "BANKNIFTY": False,
            "BTC": False,
        }
        self.stale_threshold_seconds: float = 15.0

        self._initialized = True

    def record_tick(self, symbol: str, timestamp: Optional[float] = None):
        """Records the arrival of a real tick for an instrument."""
        sym = symbol.upper()
        self.last_tick_timestamps[sym] = timestamp or time.time()
        self.subscription_status[sym] = True

    def set_provider_status(self, is_connected: bool, provider_name: Optional[str] = None):
        """Sets upstream market data provider status."""
        self.provider_connected = is_connected
        if provider_name:
            self.provider_name = provider_name

    def set_websocket_status(self, is_connected: bool, state: str = "CONNECTED"):
        """Sets WebSocket connection status."""
        self.websocket_connected = is_connected
        self.websocket_state = state.upper()

    def set_subscription(self, symbol: str, is_subscribed: bool):
        """Sets symbol subscription state."""
        self.subscription_status[symbol.upper()] = is_subscribed

    def is_session_active(self, symbol: str = "NIFTY") -> bool:
        """Determines if the financial exchange is currently in an active trading session."""
        sym = symbol.upper()
        now = datetime.datetime.now()

        # Crypto is 24/7 continuous
        if sym in ("BTC", "BITCOIN", "BTCUSD"):
            return True

        # Indian Equities / Derivatives (NSE)
        weekday = now.weekday()  # 5=Saturday, 6=Sunday
        if weekday in (5, 6):
            return False

        curr_time = (now.hour, now.minute)
        market_open = SESSION_TIMINGS.get("market_open", (9, 15))
        market_close = SESSION_TIMINGS.get("market_close", (15, 30))

        return market_open <= curr_time < market_close

    def get_status(self, symbol: str = "NIFTY") -> Dict[str, Any]:
        """
        Determines the authoritative market data status for an instrument.
        Strict Rules:
          - Never show LIVE if the provider is offline.
          - Never show LIVE if WebSocket is not receiving ticks.
          - If ticks haven't arrived in > 15s during an active session, report STALE.
          - If provider is disconnected or unauthenticated, report HISTORICAL or OFFLINE.
        """
        sym = symbol.upper()
        now = time.time()
        last_tick = self.last_tick_timestamps.get(sym, 0.0)
        tick_delta = round(now - last_tick, 1) if last_tick > 0 else 9999.0
        session_active = self.is_session_active(sym)

        # 1. Check WebSocket / Reconnecting state
        if self.websocket_state == "RECONNECTING":
            status = MarketDataStatus.RECONNECTING
            details = "WebSocket connection dropped. Reconnecting to streaming server..."

        # 2. Check for Crypto special provider
        elif sym in ("BTC", "BITCOIN", "BTCUSD"):
            # Kraken Crypto Feed
            if last_tick > 0 and tick_delta <= self.stale_threshold_seconds:
                status = MarketDataStatus.LIVE
                details = f"Kraken 24/7 Tick Feed Active (Last tick: {tick_delta:.1f}s ago)"
            elif last_tick > 0 and tick_delta > self.stale_threshold_seconds:
                status = MarketDataStatus.STALE
                details = f"Crypto ticks delayed ({tick_delta:.1f}s without tick)"
            else:
                status = MarketDataStatus.HISTORICAL
                details = "Crypto historical cached feed"

        # 3. Indian Market Feed (NSE)
        elif not self.provider_connected:
            # When DhanHQ credentials are absent or connection failed, NEVER show LIVE!
            status = MarketDataStatus.HISTORICAL
            details = "Offline / Historical Mode (DhanHQ credentials not authenticated)"

        elif not session_active:
            # Provider is authenticated, but Indian market is closed
            status = MarketDataStatus.HISTORICAL
            details = "Exchange session closed. Displaying verified historical session replay."

        elif not self.websocket_connected:
            status = MarketDataStatus.OFFLINE
            details = "Live market session active, but streaming WebSocket is disconnected."

        elif tick_delta > self.stale_threshold_seconds:
            # Expected live ticks have stalled
            status = MarketDataStatus.STALE
            details = f"Tick feed stalled during live session ({tick_delta:.1f}s > {self.stale_threshold_seconds}s threshold)."

        else:
            # Everything is healthy and ticks are arriving in real time!
            status = MarketDataStatus.LIVE
            details = f"Live real-time tick stream active (Tick latency: {tick_delta:.1f}s)"

        return {
            "symbol": sym,
            "status": status.value,
            "details": details,
            "provider_name": "Kraken Public Feed" if sym == "BTC" else self.provider_name,
            "provider_connected": self.provider_connected if sym != "BTC" else (last_tick > 0),
            "websocket_connected": self.websocket_connected,
            "websocket_state": self.websocket_state,
            "subscription_active": self.subscription_status.get(sym, False),
            "session_active": session_active,
            "last_tick_timestamp": last_tick,
            "last_tick_delta_seconds": tick_delta,
            "is_stale": (status == MarketDataStatus.STALE),
            "checked_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        }


def get_market_status_manager() -> MarketStatusManager:
    """Returns singleton instance of MarketStatusManager."""
    return MarketStatusManager()
