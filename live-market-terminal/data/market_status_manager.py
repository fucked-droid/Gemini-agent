"""
Centralized Market Data Status & Quality Manager.
Single source of truth for market data health, trading calendar, session state,
and data freshness across all monitored instruments.

Supported Operating States:
  - MARKET_OPEN: Exchange is currently inside regular active trading hours.
  - MARKET_CLOSED: Exchange session has concluded or today is a weekend/exchange holiday.
  - DATA_UNAVAILABLE: Underlying data provider unreachable or instrument data missing.

Supported Data Modes:
  - LIVE: Valid live ticks actively arriving in real-time (< 15s latency).
  - HISTORICAL: Verified historical session candle master data (market closed or offline).
  - SIMULATED: Deterministic algorithmic mock session ticks for development.
  - UNAVAILABLE: No valid data feed or candle records available.

Strict Mandates:
  - Never show LIVE if provider is offline or market is closed.
  - Never show WebSocket healthy if ticks are not arriving.
  - Track last received tick timestamp and WebSocket connection separately.
  - Standardized response envelope across every API response.
"""

import time
import datetime
from enum import Enum
from typing import Dict, Any, Optional, Set

from config import SESSION_TIMINGS

# Known NSE Trading Holidays (YYYY-MM-DD)
NSE_HOLIDAYS_2026: Set[str] = {
    "2026-01-26",  # Republic Day
    "2026-02-17",  # Mahashivratri
    "2026-03-03",  # Holi
    "2026-03-20",  # Id-Ul-Fitr (Ramzan Id)
    "2026-04-03",  # Good Friday
    "2026-04-14",  # Dr. B.R. Ambedkar Jayanti
    "2026-04-21",  # Mahavir Jayanti
    "2026-05-01",  # Maharashtra Day
    "2026-05-27",  # Bakri Id
    "2026-06-26",  # Muharram
    "2026-08-15",  # Independence Day
    "2026-09-14",  # Ganesh Chaturthi
    "2026-10-02",  # Mahatma Gandhi Jayanti
    "2026-10-20",  # Dussehra
    "2026-11-08",  # Diwali Laxmi Pujan (Muhurat session only)
    "2026-11-10",  # Diwali Balipratipada
    "2026-11-24",  # Gurunanak Jayanti
    "2026-12-25",  # Christmas
}


class OperatingState(str, Enum):
    MARKET_OPEN = "MARKET_OPEN"
    MARKET_CLOSED = "MARKET_CLOSED"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"


class DataMode(str, Enum):
    LIVE = "LIVE"
    HISTORICAL = "HISTORICAL"
    SIMULATED = "SIMULATED"
    UNAVAILABLE = "UNAVAILABLE"


class FreshnessStatus(str, Enum):
    REALTIME = "REALTIME"
    STALE = "STALE"
    CACHED = "CACHED"
    EXPIRED = "EXPIRED"
    UNAVAILABLE = "UNAVAILABLE"


class ValidityStatus(str, Enum):
    VALID = "VALID"
    DEGRADED = "DEGRADED"
    INVALID = "INVALID"


# Backward-compatible alias for existing imports
class MarketDataStatus(str, Enum):
    LIVE = "LIVE"
    HISTORICAL = "HISTORICAL"
    DELAYED = "DELAYED"
    OFFLINE = "OFFLINE"
    RECONNECTING = "RECONNECTING"
    STALE = "STALE"


# Indian Standard Time (UTC+05:30)
IST_TZ = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

class MarketStatusManager:
    """
    Centralized Authority for Feed Quality, Tick Freshness, Session Tracking,
    and Standardized Response Envelope Generation.
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
            "INDIAVIX": 0.0,
            "BTC": 0.0,
        }
        self.provider_connected: bool = False
        self.provider_name: str = "DhanHQ Official v2 API"
        self.websocket_connected: bool = False
        self.websocket_state: str = "DISCONNECTED"  # CONNECTED, CONNECTING, DISCONNECTED, RECONNECTING
        self.last_ws_message_time: float = 0.0
        self.subscription_status: Dict[str, bool] = {
            "NIFTY": False,
            "BANKNIFTY": False,
            "INDIAVIX": False,
            "BTC": False,
        }
        self.stale_threshold_seconds: float = 15.0

        self._initialized = True

    def record_tick(self, symbol: str, timestamp: Optional[float] = None):
        """Records the arrival of a real tick for an instrument."""
        sym = symbol.upper()
        now = timestamp or time.time()
        self.last_tick_timestamps[sym] = now
        self.last_ws_message_time = now
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
        if is_connected:
            self.last_ws_message_time = time.time()

    def set_subscription(self, symbol: str, is_subscribed: bool):
        """Sets symbol subscription state."""
        self.subscription_status[symbol.upper()] = is_subscribed

    def is_holiday(self, check_date: datetime.date) -> bool:
        """Determines if a date is an official NSE exchange holiday or weekend."""
        if check_date.weekday() in (5, 6):  # Saturday, Sunday
            return True
        date_str = check_date.strftime("%Y-%m-%d")
        return date_str in NSE_HOLIDAYS_2026

    def get_last_trading_session_date(self, ref_date: Optional[datetime.date] = None) -> datetime.date:
        """
        Calculates the most recent valid NSE trading session date.
        If today is a trading day and time is past 09:15, returns today.
        Otherwise steps backward until a non-holiday weekday is found.
        """
        now = datetime.datetime.now(IST_TZ)
        cur_date = ref_date or now.date()
        cur_time = (now.hour, now.minute)

        # If today is a weekend or holiday, or it's before market open (09:15)
        market_open = SESSION_TIMINGS.get("market_open", (9, 15))
        if self.is_holiday(cur_date) or cur_time < market_open:
            step = cur_date - datetime.timedelta(days=1)
            while self.is_holiday(step):
                step -= datetime.timedelta(days=1)
            return step

        return cur_date

    def get_session_details(self, symbol: str = "NIFTY") -> Dict[str, Any]:
        """Provides fine-grained session phase, market open status, and countdown message."""
        sym = symbol.upper()
        if sym in ("BTC", "BITCOIN", "BTCUSD"):
            return {
                "phase": "24_7_CONTINUOUS",
                "is_open": True,
                "status_text": "24/7 Global Crypto Active",
                "message": "Continuous 24/7 global market stream active.",
            }

        now_ist = datetime.datetime.now(IST_TZ)
        cur_date = now_ist.date()
        cur_time = (now_ist.hour, now_ist.minute)
        weekday = cur_date.weekday()

        if weekday == 5:
            return {
                "phase": "WEEKEND",
                "is_open": False,
                "status_text": "MARKET CLOSED (Saturday)",
                "message": "Market closed for the weekend. Regular trading resumes Monday at 09:15 AM IST.",
            }
        elif weekday == 6:
            return {
                "phase": "WEEKEND",
                "is_open": False,
                "status_text": "MARKET CLOSED (Sunday)",
                "message": "Market closed for the weekend. Regular trading resumes Monday at 09:15 AM IST.",
            }

        date_str = cur_date.strftime("%Y-%m-%d")
        if date_str in NSE_HOLIDAYS_2026:
            return {
                "phase": "EXCHANGE_HOLIDAY",
                "is_open": False,
                "status_text": "MARKET CLOSED (Exchange Holiday)",
                "message": f"Market closed today for designated exchange holiday ({date_str}).",
            }

        pre_start = SESSION_TIMINGS.get("pre_market_start", (9, 0))
        market_open = SESSION_TIMINGS.get("market_open", (9, 15))
        market_close = SESSION_TIMINGS.get("market_close", (15, 30))
        post_end = SESSION_TIMINGS.get("post_market_end", (16, 0))

        if cur_time < pre_start:
            return {
                "phase": "AFTER_HOURS",
                "is_open": False,
                "status_text": "MARKET CLOSED (Before Market)",
                "message": "Pre-market session opens today at 09:00 AM IST. Regular trading at 09:15 AM IST.",
            }
        elif pre_start <= cur_time < market_open:
            return {
                "phase": "PRE_MARKET",
                "is_open": False,
                "status_text": "PRE-MARKET (09:00 - 09:15 AM IST)",
                "message": "Pre-market price discovery session active. Regular trading opens at 09:15 AM IST.",
            }
        elif market_open <= cur_time < market_close:
            mins_left = (market_close[0] * 60 + market_close[1]) - (cur_time[0] * 60 + cur_time[1])
            return {
                "phase": "REGULAR_SESSION",
                "is_open": True,
                "status_text": "LIVE TRADING (09:15 - 15:30 IST)",
                "message": f"Active regular trading session. Market closes in {mins_left // 60}h {mins_left % 60}m.",
            }
        elif market_close <= cur_time < post_end:
            return {
                "phase": "POST_MARKET",
                "is_open": False,
                "status_text": "POST-MARKET (15:30 - 16:00 IST)",
                "message": "Post-market closing session. Execution locked.",
            }
        else:
            return {
                "phase": "AFTER_HOURS",
                "is_open": False,
                "status_text": "MARKET CLOSED (After Hours)",
                "message": "Trading concluded for today. Next regular session opens tomorrow at 09:15 AM IST.",
            }

    def is_session_active(self, symbol: str = "NIFTY") -> bool:
        """
        Determines if the financial exchange is currently in an active trading session.
        - BTC: Always True (24/7 continuous global market).
        - NSE (NIFTY/BANKNIFTY/INDIAVIX): True only on non-holiday weekdays between 09:15 and 15:30 IST.
        """
        return self.get_session_details(symbol)["is_open"]

    def get_operating_state(self, symbol: str = "NIFTY") -> OperatingState:
        """Returns the primary operating state: MARKET_OPEN or MARKET_CLOSED."""
        sym = symbol.upper()
        if sym in ("BTC", "BITCOIN", "BTCUSD"):
            return OperatingState.MARKET_OPEN
        return OperatingState.MARKET_OPEN if self.is_session_active(sym) else OperatingState.MARKET_CLOSED

    def get_status(self, symbol: str = "NIFTY") -> Dict[str, Any]:
        """
        Determines authoritative market data health for an instrument.
        Strict Rules:
          - Never show LIVE if provider is offline or unauthenticated.
          - Never show LIVE if market is closed.
          - Never show LIVE if WebSocket ticks are stalled (>15s).
          - Detect and label STALE prices.
          - Correctly reflect MARKET CLOSED with last session date.
        """
        sym = symbol.upper()
        now = time.time()
        now_dt = datetime.datetime.now()
        last_tick = self.last_tick_timestamps.get(sym, 0.0)
        tick_delta = round(now - last_tick, 1) if last_tick > 0 else 9999.0
        session_active = self.is_session_active(sym)
        operating_state = self.get_operating_state(sym)
        session_date = self.get_last_trading_session_date().strftime("%Y-%m-%d") if sym != "BTC" else now_dt.strftime("%Y-%m-%d")

        # 1. Check WebSocket / Reconnecting state first
        if self.websocket_state == "RECONNECTING":
            status = MarketDataStatus.RECONNECTING
            data_mode = DataMode.HISTORICAL
            freshness = FreshnessStatus.STALE
            validity = ValidityStatus.DEGRADED
            details = "WebSocket connection dropped. Reconnecting to streaming server..."

            return {
                "symbol": sym,
                "status": status.value,
                "data_mode": data_mode.value,
                "operating_state": operating_state.value,
                "freshness_status": freshness.value,
                "validity_status": validity.value,
                "details": details,
                "provider_name": self.provider_name if sym != "BTC" else "Kraken Public Feed",
                "provider_connected": self.provider_connected if sym != "BTC" else (last_tick > 0),
                "websocket_connected": False,
                "websocket_state": "RECONNECTING",
                "subscription_active": self.subscription_status.get(sym, False),
                "session_active": session_active,
                "trading_session_date": session_date,
                "last_tick_timestamp": last_tick,
                "last_tick_delta_seconds": tick_delta,
                "is_stale": True,
                "is_market_closed": (operating_state == OperatingState.MARKET_CLOSED),
                "checked_at": now_dt.strftime("%Y-%m-%d %H:%M:%S IST"),
            }

        # 2. Crypto special handling (24/7 continuous live market)
        if sym in ("BTC", "BITCOIN", "BTCUSD"):
            operating_state = OperatingState.MARKET_OPEN
            if last_tick > 0 and tick_delta <= self.stale_threshold_seconds:
                status = MarketDataStatus.LIVE
                data_mode = DataMode.LIVE
                freshness = FreshnessStatus.REALTIME
                validity = ValidityStatus.VALID
                details = f"Kraken 24/7 Tick Feed Active (Last tick: {tick_delta:.1f}s ago)"
            elif last_tick > 0 and tick_delta > self.stale_threshold_seconds:
                status = MarketDataStatus.STALE
                data_mode = DataMode.LIVE
                freshness = FreshnessStatus.STALE
                validity = ValidityStatus.DEGRADED
                details = f"Crypto ticks delayed ({tick_delta:.1f}s without tick)"
            else:
                status = MarketDataStatus.HISTORICAL
                data_mode = DataMode.HISTORICAL
                freshness = FreshnessStatus.CACHED
                validity = ValidityStatus.VALID
                details = "Crypto historical cached feed"

            return {
                "symbol": sym,
                "status": status.value,
                "data_mode": data_mode.value,
                "operating_state": operating_state.value,
                "freshness_status": freshness.value,
                "validity_status": validity.value,
                "details": details,
                "provider_name": "Kraken Public Feed",
                "provider_connected": (last_tick > 0),
                "websocket_connected": self.websocket_connected,
                "websocket_state": self.websocket_state,
                "subscription_active": self.subscription_status.get(sym, False),
                "session_active": True,
                "trading_session_date": session_date,
                "last_tick_timestamp": last_tick,
                "last_tick_delta_seconds": tick_delta,
                "is_stale": (freshness == FreshnessStatus.STALE),
                "is_market_closed": False,
                "checked_at": now_dt.strftime("%Y-%m-%d %H:%M:%S IST"),
            }

        # 2. Indian Market Feed (NSE)
        # Condition A: MARKET CLOSED
        if not session_active:
            status = MarketDataStatus.HISTORICAL
            data_mode = DataMode.HISTORICAL
            freshness = FreshnessStatus.CACHED
            validity = ValidityStatus.VALID
            details = f"MARKET CLOSED. Official closing data for session {session_date} displayed."

        # Condition B: MARKET OPEN, but provider offline or credentials missing
        elif not self.provider_connected:
            status = MarketDataStatus.HISTORICAL
            data_mode = DataMode.HISTORICAL
            freshness = FreshnessStatus.CACHED
            validity = ValidityStatus.DEGRADED
            details = "Market open, but DhanHQ feed is not authenticated. Displaying historical session benchmark."

        # Condition C: MARKET OPEN, WebSocket reconnecting
        elif self.websocket_state == "RECONNECTING":
            status = MarketDataStatus.RECONNECTING
            data_mode = DataMode.HISTORICAL
            freshness = FreshnessStatus.STALE
            validity = ValidityStatus.DEGRADED
            details = "WebSocket connection dropped. Reconnecting to streaming server..."

        # Condition D: MARKET OPEN, WebSocket disconnected
        elif not self.websocket_connected:
            status = MarketDataStatus.OFFLINE
            data_mode = DataMode.UNAVAILABLE
            freshness = FreshnessStatus.UNAVAILABLE
            validity = ValidityStatus.INVALID
            details = "Market open, but streaming WebSocket is disconnected."

        # Condition E: MARKET OPEN, but ticks stalled (>15s)
        elif tick_delta > self.stale_threshold_seconds:
            status = MarketDataStatus.STALE
            data_mode = DataMode.LIVE
            freshness = FreshnessStatus.STALE
            validity = ValidityStatus.DEGRADED
            details = f"Tick feed stalled during active session ({tick_delta:.1f}s > {self.stale_threshold_seconds}s threshold)."

        # Condition F: MARKET OPEN, verified real-time ticks flowing
        else:
            status = MarketDataStatus.LIVE
            data_mode = DataMode.LIVE
            freshness = FreshnessStatus.REALTIME
            validity = ValidityStatus.VALID
            details = f"Live real-time tick stream active (Tick latency: {tick_delta:.1f}s)"

        sess = self.get_session_details(sym)
        data_source_str = (self.provider_name if (session_active and self.provider_connected) 
                           else f"Historical Parquet Master ({session_date})")

        return {
            "symbol": sym,
            "status": status.value,
            "data_mode": data_mode.value,
            "operating_state": operating_state.value,
            "freshness_status": freshness.value,
            "validity_status": validity.value,
            "details": details,
            "provider_name": self.provider_name,
            "provider_connected": self.provider_connected,
            "data_source": data_source_str,
            "websocket_connected": self.websocket_connected,
            "websocket_state": self.websocket_state,
            "subscription_active": self.subscription_status.get(sym, False),
            "session_active": session_active,
            "session_phase": sess["phase"],
            "session_status_text": sess["status_text"],
            "session_message": sess["message"],
            "trading_session_date": session_date,
            "last_tick_timestamp": last_tick,
            "last_tick_delta_seconds": tick_delta,
            "is_stale": (freshness == FreshnessStatus.STALE),
            "is_market_closed": (operating_state == OperatingState.MARKET_CLOSED),
            "checked_at": now_dt.strftime("%Y-%m-%d %H:%M:%S IST"),
            "last_updated": now_dt.strftime("%Y-%m-%d %H:%M:%S IST"),
        }

    def create_response_envelope(
        self,
        instrument: str,
        data_source: Optional[str] = None,
        data_mode: Optional[DataMode] = None,
        freshness_status: Optional[FreshnessStatus] = None,
        validity_status: Optional[ValidityStatus] = None,
        operating_state: Optional[OperatingState] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Constructs standardized institutional metadata envelope for any market-data response.
        Mandated fields:
          - instrument
          - data_source
          - timestamp
          - last_updated_timestamp
          - session_phase
          - session_message
          - trading_session_date
          - data_mode: LIVE, HISTORICAL, SIMULATED, UNAVAILABLE
          - freshness_status
          - validity_status
        """
        stat = self.get_status(instrument)
        now_dt = datetime.datetime.now()

        envelope = {
            "instrument": instrument.upper(),
            "data_source": data_source or stat.get("data_source", stat.get("provider_name", "DhanHQ Official v2 API")),
            "timestamp": now_dt.strftime("%Y-%m-%d %H:%M:%S IST"),
            "last_updated_timestamp": now_dt.strftime("%Y-%m-%d %H:%M:%S IST"),
            "session_phase": stat.get("session_phase", "CLOSED"),
            "session_message": stat.get("session_message", ""),
            "trading_session_date": stat.get("trading_session_date", now_dt.strftime("%Y-%m-%d")),
            "data_mode": (data_mode.value if data_mode else stat.get("data_mode", DataMode.HISTORICAL.value)),
            "operating_state": (operating_state.value if operating_state else stat.get("operating_state", OperatingState.MARKET_CLOSED.value)),
            "freshness_status": (freshness_status.value if freshness_status else stat.get("freshness_status", FreshnessStatus.CACHED.value)),
            "validity_status": (validity_status.value if validity_status else stat.get("validity_status", ValidityStatus.VALID.value)),
        }

        if payload:
            envelope.update(payload)

        return envelope


def get_market_status_manager() -> MarketStatusManager:
    """Returns singleton instance of MarketStatusManager."""
    return MarketStatusManager()
