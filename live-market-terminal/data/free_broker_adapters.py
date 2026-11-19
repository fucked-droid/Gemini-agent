"""
Free Broker & Public Market Data Adapters for Live Indian Market Terminal.
Supports 100% Free Indian Broker APIs and Zero-Auth Public Market Feeds:
1. Public NSE & Yahoo Finance Feed (Zero-Auth, No Account Required, 100% Free)
2. Shoonya by Finvasia (100% Lifetime Free Brokerage & Zero-Cost Trading API)
3. Angel One SmartAPI (100% Free API, WebSocket Streaming & Historical Data)
4. Fyers API v3 (100% Free API for Account Holders)
"""

import os
import sys
import time
import logging
from typing import Dict, Any, Optional, List
import pandas as pd

from config import get_ist_now, IST_TZ

logger = logging.getLogger("FreeBrokerAdapters")


class BaseBrokerAdapter:
    """Base interface for broker & data provider connections."""
    def __init__(self, name: str):
        self.name = name
        self.is_connected = False

    def connect(self) -> bool:
        raise NotImplementedError

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def get_historical_candles(self, symbol: str, interval: str = "5m", days: int = 3) -> Optional[pd.DataFrame]:
        raise NotImplementedError


class ShoonyaAdapter(BaseBrokerAdapter):
    """
    Shoonya by Finvasia API Adapter.
    - API Cost: 100% FREE forever (₹0 subscription).
    - Brokerage: ₹0 across all segments (Equity, F&O, Currency, Commodity).
    - Account: Free opening, ₹0 AMC.
    - Python SDK: NorenRestApiPy
    """
    def __init__(
        self,
        user_id: Optional[str] = None,
        password: Optional[str] = None,
        totp_key: Optional[str] = None,
        api_key: Optional[str] = None,
        imei: Optional[str] = None,
    ):
        super().__init__("Shoonya by Finvasia (Free API)")
        self.user_id = user_id or os.getenv("SHOONYA_USER_ID", "")
        self.password = password or os.getenv("SHOONYA_PASSWORD", "")
        self.totp_key = totp_key or os.getenv("SHOONYA_TOTP_KEY", "")
        self.api_key = api_key or os.getenv("SHOONYA_API_KEY", "")
        self.imei = imei or os.getenv("SHOONYA_IMEI", "WEB_TERMINAL")
        self.api = None

    def connect(self) -> bool:
        """Authenticates with Shoonya REST API using TOTP."""
        if not (self.user_id and self.password and self.api_key):
            logger.info("Shoonya credentials not fully provided. Falling back to Public Real-Time Feed.")
            return False

        try:
            # Try importing NorenRestApiPy if installed
            from NorenRestApiPy.NorenApi import NorenApi
            import pyotp

            self.api = NorenApi()
            totp = pyotp.TOTP(self.totp_key).now() if self.totp_key else ""
            ret = self.api.login(
                userid=self.user_id,
                password=self.password,
                twoFA=totp,
                vendor_code=self.api_key,
                api_secret=self.api_key,
                imei=self.imei,
            )
            if ret and ret.get("stat") == "Ok":
                self.is_connected = True
                logger.info(f"Successfully authenticated with {self.name}.")
                return True
            else:
                logger.warning(f"Shoonya login response: {ret}")
                return False
        except ImportError:
            logger.info("NorenRestApiPy / pyotp not installed. Install with `pip install NorenRestApiPy pyotp` to enable direct Shoonya trading.")
            return False
        except Exception as e:
            logger.warning(f"Failed to connect to Shoonya API: {e}")
            return False

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        if not self.is_connected or not self.api:
            return None
        # Symbol mapping for Shoonya exchange segments
        token_map = {"NIFTY": ("NSE", "26000"), "BANKNIFTY": ("NSE", "26009")}
        exch, token = token_map.get(symbol.upper(), ("NSE", ""))
        if not token:
            return None
        try:
            q = self.api.get_quotes(exchange=exch, token=token)
            if q and q.get("stat") == "Ok":
                ltp = float(q.get("lp", 0.0))
                close = float(q.get("c", ltp))
                chg = ltp - close
                chg_pct = (chg / close * 100.0) if close != 0 else 0.0
                return {
                    "symbol": symbol.upper(),
                    "name": f"{symbol.upper()} 50" if symbol.upper() == "NIFTY" else symbol.upper(),
                    "security_id": token,
                    "exchange": "NSE_INDEX",
                    "price": round(ltp, 2),
                    "change": round(chg, 2),
                    "change_pct": round(chg_pct, 2),
                    "high": float(q.get("h", ltp)),
                    "low": float(q.get("l", ltp)),
                    "open": float(q.get("o", ltp)),
                    "close": close,
                    "volume": int(q.get("v", 1000000)),
                    "timestamp": get_ist_now().strftime("%Y-%m-%d %H:%M:%S IST"),
                    "is_live": True,
                    "source": "SHOONYA_API_LIVE",
                }
        except Exception as e:
            logger.debug(f"Shoonya get_quote failed for {symbol}: {e}")
        return None


class AngelOneAdapter(BaseBrokerAdapter):
    """
    Angel One SmartAPI Adapter.
    - API Cost: 100% FREE (₹0 subscription).
    - Brokerage: ₹0 Delivery, Flat ₹20 F&O / Intraday.
    - Python SDK: smartapi-python
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        client_code: Optional[str] = None,
        pin: Optional[str] = None,
        totp_secret: Optional[str] = None,
    ):
        super().__init__("Angel One SmartAPI (Official Free)")
        from .angel_provider import get_angel_provider
        self.provider = get_angel_provider()
        self.api_key = api_key or self.provider.api_key
        self.client_code = client_code or self.provider.client_code
        self.pin = pin or self.provider.pin
        self.totp_secret = totp_secret or self.provider.totp_secret
        self.smart_api = None

    def connect(self) -> bool:
        """Authenticates with Angel One SmartAPI and initializes streaming."""
        success = self.provider.authenticate()
        if success:
            self.is_connected = True
            self.smart_api = self.provider.smart_api
            logger.info(f"Successfully authenticated with {self.name}.")
            # Start streaming and candle pre-fetch
            try:
                self.provider.fetch_startup_candles()
                self.provider.start_websocket_stream()
            except Exception as se:
                logger.warning(f"Startup streaming hook warning: {se}")
            return True
        else:
            self.is_connected = False
            return False

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        if not self.is_connected:
            return None
        from .market_cache import get_global_cache
        cache = get_global_cache()
        # 1. Check live WebSocket / memory quote cache
        if symbol.upper() in cache.quotes:
            q = cache.quotes[symbol.upper()]
            if q and q.get("source") in ("ANGEL_SMARTWS_LIVE", "ANGEL_SMARTAPI_STARTUP", "ANGEL_SMARTAPI_LIVE"):
                return q

        # 2. Query SmartAPI REST ltpData
        token_map = {"NIFTY": ("NSE", "99926000"), "BANKNIFTY": ("NSE", "99926009"), "INDIAVIX": ("NSE", "99926017")}
        exch, token = token_map.get(symbol.upper(), ("NSE", ""))
        if not token or not self.provider.smart_api:
            return None
        try:
            q = self.provider.smart_api.ltpData(exch, symbol.upper(), token)
            if q and q.get("status"):
                d = q.get("data", {})
                ltp = float(d.get("ltp", 0.0))
                close = float(d.get("close", ltp))
                chg = ltp - close
                chg_pct = (chg / close * 100.0) if close != 0 else 0.0
                quote_obj = {
                    "symbol": symbol.upper(),
                    "name": f"{symbol.upper()} 50" if symbol.upper() == "NIFTY" else symbol.upper(),
                    "security_id": token,
                    "exchange": "NSE_INDEX",
                    "price": round(ltp, 2),
                    "change": round(chg, 2),
                    "change_pct": round(chg_pct, 2),
                    "high": float(d.get("high", ltp)),
                    "low": float(d.get("low", ltp)),
                    "open": float(d.get("open", ltp)),
                    "close": close,
                    "volume": int(d.get("volume", 1000000)),
                    "timestamp": get_ist_now().strftime("%Y-%m-%d %H:%M:%S IST"),
                    "is_live": True,
                    "source": "ANGEL_SMARTAPI_LIVE",
                }
                cache.update_quote(symbol.upper(), quote_obj)
                return quote_obj
        except Exception as e:
            logger.debug(f"Angel One get_quote failed for {symbol}: {e}")
        return None

    def get_historical_candles(self, symbol: str, interval: str = "5m", days: int = 5) -> Optional[pd.DataFrame]:
        """Returns 5m candles from Angel One SmartAPI."""
        sym = symbol.upper()
        if sym in self.provider.cached_candles:
            return self.provider.cached_candles[sym]
        candles_dict = self.provider.fetch_startup_candles(days=days)
        return candles_dict.get(sym)

    def get_futures_metrics(self) -> Dict[str, Any]:
        """Returns real-time VWAP, tick-rule CVD, buyer/seller pressure from NIFTY Futures."""
        return self.provider.get_futures_metrics()
