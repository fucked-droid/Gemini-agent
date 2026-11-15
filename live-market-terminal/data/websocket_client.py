"""
DhanHQ WebSocket Client for Live Tick Streaming.
Maintains persistent background connection, handles reconnects,
parses binary/JSON tick packets, and streams data into the central MarketCache.
"""

import time
import threading
import logging
from typing import List, Tuple, Optional, Any
from config import DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN, DHAN_WSS_URL
from .market_cache import get_global_cache
from .market_status_manager import get_market_status_manager

logger = logging.getLogger("DhanWebSocketClient")

class DhanWebSocketClient:
    """
    Asynchronous tick streaming client using official dhanhq MarketFeed
    or resilient background worker thread.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        access_token: Optional[str] = None,
        instruments: Optional[List[Tuple[str, str]]] = None,
    ):
        self.client_id = client_id or DHAN_CLIENT_ID
        self.access_token = access_token or DHAN_ACCESS_TOKEN
        # Instruments format: [(ExchangeSegment, SecurityId), ...]
        self.instruments = instruments or [
            ("IDX", "13"),  # NIFTY 50
            ("IDX", "25"),  # BANKNIFTY
            ("IDX", "24"),  # INDIA VIX
        ]
        self.is_running = False
        self.is_connected = False
        self._thread: Optional[threading.Thread] = None
        self._cache = get_global_cache()
        self._feed = None

    def start(self):
        """Starts the WebSocket worker in a daemon thread."""
        if self.is_running:
            return

        if not self.client_id or not self.access_token:
            logger.info("WebSocket: Missing credentials. Real-time tick stream idle (using REST poll fallback).")
            self._cache.update_system_status("WEBSOCKET_OFFLINE", "No credentials configured")
            get_market_status_manager().set_websocket_status(False, "DISCONNECTED")
            return

        self.is_running = True
        self._thread = threading.Thread(target=self._run_loop, name="DhanWSSWorker", daemon=True)
        self._thread.start()
        logger.info("Dhan WebSocket client thread started.")

    def stop(self):
        """Stops the WebSocket streaming thread."""
        self.is_running = False
        self.is_connected = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Dhan WebSocket client stopped.")

    def _run_loop(self):
        """Background connection and retry loop."""
        backoff = 2
        while self.is_running:
            try:
                logger.info("Initializing Dhan MarketFeed WebSocket connection...")
                from dhanhq import DhanContext, MarketFeed

                dhan_context = DhanContext(self.client_id, self.access_token)
                sub_instruments = [
                    (seg, sec_id, MarketFeed.Full)
                    for (seg, sec_id) in self.instruments
                ]
                self._feed = MarketFeed(dhan_context, sub_instruments, "v2")
                self.is_connected = True
                self._cache.update_system_status("CONNECTED", "WebSocket live feed active")
                get_market_status_manager().set_websocket_status(True, "CONNECTED")
                for _, sec_id in self.instruments:
                    get_market_status_manager().set_subscription(sec_id, True)

                # Run feed
                self._feed.run_forever()

                while self.is_running and self.is_connected:
                    data = self._feed.get_data()
                    if data:
                        self._process_tick(data)
                    else:
                        time.sleep(0.05)

            except Exception as e:
                self.is_connected = False
                self._cache.update_system_status("RECONNECTING", f"WebSocket error: {e}")
                get_market_status_manager().set_websocket_status(False, "RECONNECTING")
                logger.warning(f"WebSocket disconnected ({e}). Reconnecting in {backoff}s...")
                time.sleep(backoff)
                backoff = min(backoff * 2, 30)

    def _process_tick(self, data: Any):
        """Dispatches incoming tick to central MarketCache."""
        try:
            if isinstance(data, dict):
                sec_id = str(data.get("security_id", data.get("SecurityId", "")))
                ltp = float(data.get("LTP", data.get("last_price", 0.0)))
                vol = int(data.get("volume", data.get("Volume", 0)))
                if ltp > 0:
                    self._cache.update_tick(sec_id, ltp, vol)
        except Exception as e:
            logger.debug(f"Error handling tick data: {e}")
