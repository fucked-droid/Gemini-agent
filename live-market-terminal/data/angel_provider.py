"""
Angel One SmartAPI Provider & Real-Time WebSocket Streaming Engine.
Handles:
1. Dynamic TOTP authentication & proactive 08:50 AM IST daily session renewal.
2. Startup 5-day FIVE_MINUTE candle loading for NIFTY (99926000), BANKNIFTY (99926009), INDIA VIX (99926017).
3. Dynamic nearest monthly NIFTY NFO FUTIDX contract resolution from OpenAPIScripMaster.json.
4. SmartWebSocketV2 (mode 3) streaming with price scaling (/ 100.0).
5. Real-time VWAP, tick-rule CVD, and Buyer/Seller pressure calculation from NIFTY Futures.
"""

import os
import sys
import time
import json
import logging
import datetime
import threading
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

import pandas as pd
import numpy as np

# Ensure path resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
SCRIP_MASTER_FILE = CACHE_DIR / "OpenAPIScripMaster.json"
SCRIP_MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

from config import get_ist_now, IST_TZ
from .market_status_manager import get_market_status_manager
from .market_cache import get_global_cache

logger = logging.getLogger("AngelOneProvider")

# Symbol to token mapping for Indian spot indices on NSE
SPOT_TOKENS = {
    "NIFTY": {"exchange": "NSE", "exchange_type": 1, "token": "99926000", "name": "NIFTY 50"},
    "BANKNIFTY": {"exchange": "NSE", "exchange_type": 1, "token": "99926009", "name": "NIFTY BANK"},
    "INDIAVIX": {"exchange": "NSE", "exchange_type": 1, "token": "99926017", "name": "INDIA VIX"},
}
TOKEN_TO_SYMBOL = {v["token"]: k for k, v in SPOT_TOKENS.items()}


class AngelOneProvider:
    """
    Singleton manager for Angel One SmartAPI, Historical Candles,
    Dynamic Futures Resolution, and SmartWebSocketV2 Streaming.
    """

    _instance: Optional["AngelOneProvider"] = None

    @classmethod
    def get_instance(cls) -> "AngelOneProvider":
        if cls._instance is None:
            cls._instance = AngelOneProvider()
        return cls._instance

    def __init__(self):
        self.api_key = os.getenv("ANGEL_API_KEY", "")
        self.client_code = os.getenv("ANGEL_CLIENT_ID") or os.getenv("ANGEL_CLIENT_CODE", "")
        self.pin = os.getenv("ANGEL_MPIN") or os.getenv("ANGEL_PIN", "")
        self.totp_secret = os.getenv("ANGEL_TOTP_SECRET", "")

        self.smart_api = None
        self.jwt_token: str = ""
        self.refresh_token: str = ""
        self.feed_token: str = ""
        self.is_authenticated: bool = False
        self.last_login_time: float = 0.0
        self.last_daily_refresh_date: Optional[datetime.date] = None

        # Nearest dynamic NIFTY NFO Future
        self.nearest_nifty_future: Optional[Dict[str, Any]] = None
        self.future_token: str = ""

        # Futures Real-Time Metrics State
        self._prev_fut_price: Optional[float] = None
        self._last_tick_dir: int = 1  # 1 = uptick, -1 = downtick
        self._fut_cvd: int = 0
        self._cum_buy_vol: float = 0.0
        self._cum_sell_vol: float = 0.0
        self._running_pv: float = 0.0
        self._running_vol: float = 0.0

        self.futures_metrics: Dict[str, Any] = {
            "vwap": 0.0,
            "cvd": 0,
            "session_cvd": 0,
            "buyer_percentage": 50.0,
            "seller_percentage": 50.0,
            "fut_price": 0.0,
            "total_buy_quantity": 0.0,
            "total_sell_quantity": 0.0,
            "volume": 0,
            "open_interest": 0,
            "contract": "NIFTY_FUT",
            "updated_at": "",
        }

        # WebSocket State
        self.ws_client = None
        self.ws_thread: Optional[threading.Thread] = None
        self.ws_running: bool = False

        # Cached Candles
        self.cached_candles: Dict[str, pd.DataFrame] = {}

    def authenticate(self) -> bool:
        """Authenticates with Angel One SmartAPI using TOTP."""
        if not (self.api_key and self.client_code and self.pin and self.totp_secret):
            logger.warning("Angel One credentials incomplete in .env.")
            return False

        try:
            from SmartApi import SmartConnect
            import pyotp

            self.smart_api = SmartConnect(api_key=self.api_key)
            totp = pyotp.TOTP(self.totp_secret).now()
            session = self.smart_api.generateSession(self.client_code, self.pin, totp)

            if session and session.get("status"):
                data = session.get("data", {})
                self.jwt_token = data.get("jwtToken", "")
                self.refresh_token = data.get("refreshToken", "")
                self.feed_token = self.smart_api.getfeedToken()
                self.is_authenticated = True
                self.last_login_time = time.time()
                self.last_daily_refresh_date = get_ist_now().date()

                mgr = get_market_status_manager()
                mgr.set_provider_status(True, "Angel One SmartAPI (Official Free)")
                logger.info(f"Successfully authenticated with Angel One SmartAPI (Client: {self.client_code}).")
                return True
            else:
                logger.error(f"Angel One SmartAPI authentication failed: {session}")
                self.is_authenticated = False
                return False

        except Exception as e:
            logger.error(f"Error during Angel One authentication: {e}")
            self.is_authenticated = False
            return False

    def check_and_refresh_session(self) -> bool:
        """
        Proactively re-authenticates the SmartAPI session every morning
        at 08:50 AM IST before the 09:15 AM IST market open.
        """
        now_ist = get_ist_now()
        today = now_ist.date()

        # Check if it is >= 08:50 AM IST and haven't refreshed today
        is_refresh_window = (now_ist.hour == 8 and now_ist.minute >= 50) or (now_ist.hour > 8)
        if is_refresh_window and (self.last_daily_refresh_date != today):
            logger.info(f"Triggering scheduled 08:50 AM IST session refresh (Current: {now_ist.strftime('%H:%M:%S IST')})...")
            success = self.authenticate()
            if success:
                logger.info("08:50 AM IST SmartAPI session refreshed successfully. Reconnecting WebSocket...")
                if self.ws_running:
                    self.restart_websocket_stream()
            return success
        return False

    def fetch_startup_candles(self, days: int = 5) -> Dict[str, pd.DataFrame]:
        """
        Requirement 1:
        Calls getCandleData (FIVE_MINUTE, last 5 days) for:
        - NIFTY 50 (99926000)
        - BANKNIFTY (99926009)
        - INDIA VIX (99926017)
        Populates cached candles immediately so charts and indicators
        populate on startup even when NSE is closed.
        """
        if not self.is_authenticated:
            self.authenticate()

        if not self.is_authenticated or not self.smart_api:
            logger.warning("Cannot fetch startup candles: SmartAPI not authenticated.")
            return {}

        now = get_ist_now()
        from_dt = (now - datetime.timedelta(days=days)).strftime("%Y-%m-%d 09:15")
        to_dt = now.strftime("%Y-%m-%d 15:30")

        results = {}
        for sym, meta in SPOT_TOKENS.items():
            try:
                param = {
                    "exchange": meta["exchange"],
                    "symboltoken": meta["token"],
                    "interval": "FIVE_MINUTE",
                    "fromdate": from_dt,
                    "todate": to_dt,
                }
                res = self.smart_api.getCandleData(param)
                if res and res.get("status") and res.get("data"):
                    raw = res["data"]
                    df = pd.DataFrame(raw, columns=["Datetime", "Open", "High", "Low", "Close", "Volume"])
                    df["Datetime"] = pd.to_datetime(df["Datetime"])
                    df.set_index("Datetime", inplace=True)
                    for col in ["Open", "High", "Low", "Close"]:
                        df[col] = df[col].astype(float)
                    df["Volume"] = df["Volume"].astype(int)

                    results[sym] = df
                    self.cached_candles[sym] = df
                    logger.info(f"Loaded {len(df)} 5-minute startup candles for {sym} (Token {meta['token']}).")

                    # Also update latest quote from the last candle
                    last_bar = df.iloc[-1]
                    prev_close = float(df.iloc[-2]["Close"]) if len(df) > 1 else float(last_bar["Close"])
                    close_p = float(last_bar["Close"])
                    chg = close_p - prev_close
                    chg_pct = (chg / prev_close * 100.0) if prev_close != 0 else 0.0

                    quote_payload = {
                        "symbol": sym,
                        "name": meta["name"],
                        "security_id": meta["token"],
                        "exchange": "NSE_INDEX",
                        "price": round(close_p, 2),
                        "change": round(chg, 2),
                        "change_pct": round(chg_pct, 2),
                        "high": round(float(df["High"].max()), 2),
                        "low": round(float(df["Low"].min()), 2),
                        "open": round(float(df.iloc[0]["Open"]), 2),
                        "close": round(close_p, 2),
                        "volume": int(df["Volume"].sum()) or 1000000,
                        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S IST"),
                        "is_live": True,
                        "source": "ANGEL_SMARTAPI_STARTUP",
                    }
                    get_global_cache().update_quote(sym, quote_payload)
                    get_market_status_manager().record_tick(sym)
                else:
                    logger.warning(f"Could not fetch candle data for {sym}: {res}")
            except Exception as e:
                logger.error(f"Error fetching startup candles for {sym}: {e}")

        return results

    def resolve_nearest_nifty_future(self) -> Optional[Dict[str, Any]]:
        """
        Requirement 2:
        Dynamically resolves the nearest monthly NIFTY NFO FUTIDX contract
        from OpenAPIScripMaster.json (never hardcode expiry tokens).
        """
        # Ensure Scrip Master exists and is fresh (< 24 hours old)
        need_download = True
        if SCRIP_MASTER_FILE.exists():
            age_hours = (time.time() - SCRIP_MASTER_FILE.stat().st_mtime) / 3600.0
            if age_hours < 24.0 and SCRIP_MASTER_FILE.stat().st_size > 1000000:
                need_download = False

        if need_download:
            logger.info("Downloading latest OpenAPIScripMaster.json from Angel One...")
            try:
                req = urllib.request.Request(SCRIP_MASTER_URL, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = resp.read()
                with open(SCRIP_MASTER_FILE, "wb") as f:
                    f.write(data)
                logger.info(f"OpenAPIScripMaster.json downloaded successfully ({len(data)} bytes).")
            except Exception as e:
                logger.warning(f"Failed to download OpenAPIScripMaster.json: {e}. Using cached version if available.")

        if not SCRIP_MASTER_FILE.exists():
            logger.error("Scrip master file does not exist.")
            return None

        try:
            with open(SCRIP_MASTER_FILE, "r", encoding="utf-8") as f:
                scrips = json.load(f)

            today = get_ist_now().date()
            candidates = []
            for s in scrips:
                # Filter for NIFTY FUTIDX in NFO
                if (
                    s.get("exch_seg") == "NFO"
                    and s.get("instrumenttype") == "FUTIDX"
                    and s.get("name") == "NIFTY"
                ):
                    expiry_str = s.get("expiry", "")
                    try:
                        exp_date = datetime.datetime.strptime(expiry_str, "%d%b%Y").date()
                        if exp_date >= today:
                            candidates.append((exp_date, s))
                    except Exception:
                        pass

            if not candidates:
                logger.error("No valid unexpired NIFTY FUTIDX contracts found in Scrip Master.")
                return None

            # Sort by earliest expiry date >= today
            candidates.sort(key=lambda x: x[0])
            nearest = candidates[0][1]
            self.nearest_nifty_future = nearest
            self.future_token = str(nearest["token"])
            logger.info(
                f"Dynamically resolved nearest NIFTY FUTIDX contract: {nearest.get('symbol')} "
                f"(Token: {self.future_token}, Expiry: {nearest.get('expiry')})"
            )
            return nearest

        except Exception as e:
            logger.error(f"Error parsing OpenAPIScripMaster.json: {e}")
            return None

    def start_websocket_stream(self):
        """
        Requirement 2 & 3:
        Starts SmartWebSocketV2 (mode 3) streaming for spot indices and
        dynamically resolved NIFTY FUTIDX contract in a background thread.
        """
        if self.ws_running and self.ws_thread and self.ws_thread.is_alive():
            return

        if not self.is_authenticated:
            self.authenticate()

        if not self.is_authenticated:
            logger.warning("Cannot start SmartWebSocketV2: Not authenticated.")
            return

        if not self.nearest_nifty_future:
            self.resolve_nearest_nifty_future()

        self.ws_running = True
        self.ws_thread = threading.Thread(target=self._run_smart_websocket, daemon=True, name="SmartWSWorker")
        self.ws_thread.start()
        logger.info("SmartWebSocketV2 streaming thread started.")

    def restart_websocket_stream(self):
        """Restarts WebSocket stream (e.g. after session refresh)."""
        logger.info("Restarting SmartWebSocketV2 stream...")
        self.stop_websocket_stream()
        time.sleep(1.0)
        self.start_websocket_stream()

    def stop_websocket_stream(self):
        """Stops active WebSocket connection."""
        self.ws_running = False
        if self.ws_client:
            try:
                self.ws_client.close_connection()
            except Exception:
                pass
            self.ws_client = None

    def _run_smart_websocket(self):
        """Background thread executing SmartWebSocketV2 loop."""
        from SmartApi.smartWebSocketV2 import SmartWebSocketV2

        while self.ws_running:
            try:
                self.ws_client = SmartWebSocketV2(
                    auth_token=self.jwt_token,
                    api_key=self.api_key,
                    client_code=self.client_code,
                    feed_token=self.feed_token,
                    max_retry_attempt=5,
                    retry_strategy=1,
                    retry_delay=5,
                    retry_multiplier=1.5,
                    retry_duration=60,
                )

                def on_open(wsapp):
                    logger.info("SmartWebSocketV2 connected. Subscribing in Mode 3 (SNAP_QUOTE)...")
                    token_list = [
                        {"exchangeType": 1, "tokens": ["99926000", "99926009", "99926017"]},
                    ]
                    if self.future_token:
                        token_list.append({"exchangeType": 2, "tokens": [self.future_token]})

                    self.ws_client.subscribe("terminal_snap", 3, token_list)
                    logger.info(f"Subscribed to spot tokens + NIFTY Future ({self.future_token}) in Mode 3.")

                def on_data(wsapp, data):
                    try:
                        self._handle_ws_tick(data)
                    except Exception as he:
                        logger.debug(f"Error handling SmartWS tick: {he}")

                def on_error(wsapp, error):
                    logger.warning(f"SmartWebSocketV2 error: {error}")

                def on_close(wsapp):
                    logger.info("SmartWebSocketV2 closed.")

                self.ws_client.on_open = on_open
                self.ws_client.on_data = on_data
                self.ws_client.on_error = on_error
                self.ws_client.on_close = on_close

                self.ws_client.connect()
            except Exception as e:
                logger.warning(f"SmartWebSocketV2 exception: {e}")

            if self.ws_running:
                time.sleep(3.0)

    def _handle_ws_tick(self, data: Dict[str, Any]):
        """
        Processes incoming Mode 3 (SNAP_QUOTE) ticks.
        Rule: DIVIDE ALL incoming last_traded_price values by 100.0.
        """
        token = str(data.get("token", ""))
        raw_ltp = data.get("last_traded_price", 0)
        if raw_ltp == 0:
            return

        # Divide all prices by 100.0 (Angel One sends in paise)
        ltp = round(float(raw_ltp) / 100.0, 2)
        atp = round(float(data.get("average_traded_price", 0)) / 100.0, 2)
        open_p = round(float(data.get("open_price_of_the_day", 0)) / 100.0, 2)
        high_p = round(float(data.get("high_price_of_the_day", 0)) / 100.0, 2)
        low_p = round(float(data.get("low_price_of_the_day", 0)) / 100.0, 2)
        close_p = round(float(data.get("closed_price", 0)) / 100.0, 2)

        now_str = get_ist_now().strftime("%Y-%m-%d %H:%M:%S IST")
        cache = get_global_cache()
        mgr = get_market_status_manager()

        # 1. Spot Indices Handling
        if token in TOKEN_TO_SYMBOL:
            sym = TOKEN_TO_SYMBOL[token]
            prev_q = cache.quotes.get(sym, {})
            prev_close = close_p if close_p > 0 else (prev_q.get("close") or ltp)
            chg = round(ltp - prev_close, 2)
            chg_pct = round((chg / prev_close * 100.0), 2) if prev_close != 0 else 0.0

            q_update = {
                "symbol": sym,
                "name": SPOT_TOKENS[sym]["name"],
                "security_id": token,
                "exchange": "NSE_INDEX",
                "price": ltp,
                "change": chg,
                "change_pct": chg_pct,
                "high": high_p or ltp,
                "low": low_p or ltp,
                "open": open_p or ltp,
                "close": prev_close,
                "volume": int(data.get("volume_trade_for_the_day", 0)) or prev_q.get("volume", 1000000),
                "timestamp": now_str,
                "is_live": True,
                "source": "ANGEL_SMARTWS_LIVE",
            }
            cache.update_quote(sym, q_update)
            mgr.record_tick(sym)

        # 2. NIFTY Futures Contract Handling (Requirement 3)
        elif self.future_token and token == self.future_token:
            qty = int(data.get("last_traded_quantity", 0))
            vol = int(data.get("volume_trade_for_the_day", 0))
            oi = int(data.get("open_interest", 0))
            total_buy = float(data.get("total_buy_quantity", 0.0))
            total_sell = float(data.get("total_sell_quantity", 0.0))

            # A. Compute Real-Time VWAP
            # Mode 3 provides exchange average_traded_price (/ 100.0) directly
            if atp > 0:
                current_vwap = atp
            else:
                if qty > 0:
                    self._running_pv += ltp * qty
                    self._running_vol += qty
                current_vwap = round(self._running_pv / self._running_vol, 2) if self._running_vol > 0 else ltp

            # B. Compute Tick-Rule Cumulative Volume Delta (CVD)
            if self._prev_fut_price is not None and qty > 0:
                if ltp > self._prev_fut_price:
                    self._last_tick_dir = 1
                elif ltp < self._prev_fut_price:
                    self._last_tick_dir = -1
                # If price unchanged, keep previous tick direction (standard tick rule)
                delta = self._last_tick_dir * qty
                self._fut_cvd += delta

                if self._last_tick_dir > 0:
                    self._cum_buy_vol += qty
                else:
                    self._cum_sell_vol += qty
            self._prev_fut_price = ltp

            # C. Compute Buyer/Seller Pressure Percentage
            # Use exchange market depth order book totals if available, otherwise tick-rule flow
            if (total_buy + total_sell) > 0:
                buyer_pct = round((total_buy / (total_buy + total_sell)) * 100.0, 1)
            elif (self._cum_buy_vol + self._cum_sell_vol) > 0:
                buyer_pct = round((self._cum_buy_vol / (self._cum_buy_vol + self._cum_sell_vol)) * 100.0, 1)
            else:
                buyer_pct = 50.0
            seller_pct = round(100.0 - buyer_pct, 1)

            # Update metrics payload
            fut_sym = self.nearest_nifty_future.get("symbol", "NIFTY_FUT") if self.nearest_nifty_future else "NIFTY_FUT"
            self.futures_metrics = {
                "vwap": current_vwap,
                "cvd": self._fut_cvd,
                "session_cvd": self._fut_cvd,
                "buyer_percentage": buyer_pct,
                "seller_percentage": seller_pct,
                "fut_price": ltp,
                "total_buy_quantity": total_buy,
                "total_sell_quantity": total_sell,
                "volume": vol,
                "open_interest": oi,
                "contract": fut_sym,
                "updated_at": now_str,
            }

            mgr.record_tick("NIFTY")

    def get_futures_metrics(self) -> Dict[str, Any]:
        """Returns the latest real-time computed NIFTY Futures metrics."""
        return self.futures_metrics


def get_angel_provider() -> AngelOneProvider:
    """Helper singleton accessor."""
    return AngelOneProvider.get_instance()
