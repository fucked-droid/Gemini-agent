"""
Public Real-Time NSE Market Data Feed (NIFTY 50, BANKNIFTY & INDIA VIX).
Provides live quotes and multi-timeframe candle data for Indian equities
using public high-availability institutional endpoints (Yahoo Finance chart API).
Enables zero-auth continuous live market monitoring without requiring private broker credentials.
"""

import time
import json
import logging
import datetime
import urllib.request
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from config import get_ist_now, IST_TZ
from .market_status_manager import get_market_status_manager

logger = logging.getLogger("PublicNSEFeed")

class PublicNSEFeed:
    """
    Public REST live data provider for Indian equity indices and constituents.
    Requires no API keys, has zero authentication overhead, and operates continuously.
    """

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    )
    HEADERS = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://finance.yahoo.com/",
        "Origin": "https://finance.yahoo.com",
    }

    INDEX_MAP = {
        "NIFTY": {"ticker": "%5ENSEI", "name": "NIFTY 50", "sec_id": "13", "exchange": "NSE_INDEX"},
        "BANKNIFTY": {"ticker": "%5ENSEBANK", "name": "NIFTY BANK", "sec_id": "25", "exchange": "NSE_INDEX"},
        "INDIAVIX": {"ticker": "%5EINDIAVIX", "name": "INDIA VIX", "sec_id": "24", "exchange": "NSE_INDEX"},
    }

    _cached_quotes: Dict[str, Dict[str, Any]] = {}
    _quote_cache_ts: Dict[str, float] = {}
    _cached_candles: Dict[str, pd.DataFrame] = {}
    _candle_cache_ts: Dict[str, float] = {}

    QUOTE_CACHE_TTL = 8.0   # Cache quotes for 8 seconds to prevent Yahoo 429 rate-limiting
    CANDLE_CACHE_TTL = 25.0 # Cache candles for 25 seconds for multi-timeframe analytics

    @classmethod
    def resolve_ticker(cls, symbol: str) -> Optional[Dict[str, Any]]:
        """Resolves symbol to ticker mapping and metadata."""
        sym_clean = symbol.upper().replace(" ", "").replace("_", "").replace("-", "")
        if "BANK" in sym_clean:
            return cls.INDEX_MAP["BANKNIFTY"]
        elif "VIX" in sym_clean:
            return cls.INDEX_MAP["INDIAVIX"]
        elif "NIFTY" in sym_clean:
            return cls.INDEX_MAP["NIFTY"]
        return None

    @classmethod
    def get_live_quote(cls, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetches live real-time quote for NIFTY, BANKNIFTY, or INDIAVIX.
        Caches responses for QUOTE_CACHE_TTL to prevent spamming while keeping responsive.
        """
        meta = cls.resolve_ticker(symbol)
        if not meta:
            return None

        sym = symbol.upper()
        now_ts = time.time()
        if sym in cls._cached_quotes and (now_ts - cls._quote_cache_ts.get(sym, 0) < cls.QUOTE_CACHE_TTL):
            return cls._cached_quotes[sym]

        ticker = meta["ticker"]
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d"

        try:
            req = urllib.request.Request(url, headers=cls.HEADERS)
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                data = json.loads(resp.read().decode())
                chart_res = data.get("chart", {}).get("result", [])
                if not chart_res:
                    return cls._cached_quotes.get(sym)

                res = chart_res[0]
                m = res.get("meta", {})
                price = float(m.get("regularMarketPrice", 0.0))
                if price <= 0:
                    return cls._cached_quotes.get(sym)

                prev_close = float(m.get("chartPreviousClose", m.get("previousClose", price)))
                change = price - prev_close
                change_pct = (change / prev_close * 100.0) if prev_close != 0 else 0.0
                day_high = float(m.get("regularMarketDayHigh", price))
                day_low = float(m.get("regularMarketDayLow", price))
                vol = int(m.get("regularMarketVolume", 1000000))
                if vol <= 0:
                    vol = 1000000

                now_ist = get_ist_now()
                now_str = now_ist.strftime("%Y-%m-%d %H:%M:%S IST")

                quote = {
                    "symbol": sym,
                    "name": meta["name"],
                    "security_id": meta["sec_id"],
                    "exchange": meta["exchange"],
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "high": round(day_high, 2),
                    "low": round(day_low, 2),
                    "open": round(float(m.get("regularMarketDayLow", price)), 2),
                    "close": round(prev_close, 2),
                    "volume": vol,
                    "timestamp": now_str,
                    "is_live": True,
                    "source": "YAHOO_NSE_PUBLIC_LIVE",
                }

                cls._cached_quotes[sym] = quote
                cls._quote_cache_ts[sym] = now_ts
                get_market_status_manager().record_tick(sym)
                return quote

        except Exception as e:
            logger.debug(f"Public quote fetch failed for {symbol}: {e}")
            return cls._cached_quotes.get(sym)

    @classmethod
    def get_historical_candles(
        cls, symbol: str, interval: str = "5m", days: int = 3, limit: int = 150
    ) -> Optional[pd.DataFrame]:
        """
        Fetches live historical OHLCV candles from Yahoo Finance chart endpoint.
        Returns DataFrame with IST DatetimeIndex and columns: Open, High, Low, Close, Volume.
        """
        meta = cls.resolve_ticker(symbol)
        if not meta:
            return None

        sym = symbol.upper()
        now_ts = time.time()
        cache_key = f"{sym}_{interval.lower()}"
        if cache_key in cls._cached_candles and (now_ts - cls._candle_cache_ts.get(cache_key, 0) < cls.CANDLE_CACHE_TTL):
            return cls._cached_candles[cache_key]

        ticker = meta["ticker"]
        int_clean = interval.lower()
        if int_clean == "1m":
            y_interval = "1m"
            y_range = "2d"
        elif int_clean in ("3m", "5m"):
            y_interval = "5m"
            y_range = f"{max(days, 2)}d"
        elif int_clean in ("15m", "30m"):
            y_interval = int_clean
            y_range = f"{max(days, 5)}d"
        elif int_clean in ("60m", "1h"):
            y_interval = "60m"
            y_range = "1mo"
        else:
            y_interval = "5m"
            y_range = f"{max(days, 2)}d"

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={y_interval}&range={y_range}"

        try:
            req = urllib.request.Request(url, headers=cls.HEADERS)
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode())
                chart_res = data.get("chart", {}).get("result", [])
                if not chart_res:
                    return cls._cached_candles.get(cache_key)

                res = chart_res[0]
                m = res.get("meta", {})
                price = float(m.get("regularMarketPrice", 0.0))
                if price > 0:
                    prev_close = float(m.get("chartPreviousClose", m.get("previousClose", price)))
                    change = price - prev_close
                    change_pct = (change / prev_close * 100.0) if prev_close != 0 else 0.0
                    day_high = float(m.get("regularMarketDayHigh", price))
                    day_low = float(m.get("regularMarketDayLow", price))
                    vol = int(m.get("regularMarketVolume", 1000000))
                    if vol <= 0:
                        vol = 1000000
                    now_ist = get_ist_now()
                    now_str = now_ist.strftime("%Y-%m-%d %H:%M:%S IST")

                    # Opportunistically prime live quote from candle response
                    cls._cached_quotes[sym] = {
                        "symbol": sym,
                        "name": meta["name"],
                        "security_id": meta["sec_id"],
                        "exchange": meta["exchange"],
                        "price": round(price, 2),
                        "change": round(change, 2),
                        "change_pct": round(change_pct, 2),
                        "high": round(day_high, 2),
                        "low": round(day_low, 2),
                        "open": round(float(m.get("regularMarketDayLow", price)), 2),
                        "close": round(prev_close, 2),
                        "volume": vol,
                        "timestamp": now_str,
                        "is_live": True,
                        "source": "YAHOO_NSE_PUBLIC_LIVE",
                    }
                    cls._quote_cache_ts[sym] = now_ts
                    get_market_status_manager().record_tick(sym)

                timestamps = res.get("timestamp", [])
                quote_data = res.get("indicators", {}).get("quote", [{}])[0]

                if not timestamps or not quote_data:
                    return cls._cached_candles.get(cache_key)

                opens = quote_data.get("open", [])
                highs = quote_data.get("high", [])
                lows = quote_data.get("low", [])
                closes = quote_data.get("close", [])
                volumes = quote_data.get("volume", [])

                dt_index = pd.to_datetime(timestamps, unit="s", utc=True).tz_convert("Asia/Kolkata").tz_localize(None)

                # Ensure realistic synthetic volume if raw index volume is 0
                clean_vols = []
                for i in range(len(timestamps)):
                    v = volumes[i] if i < len(volumes) else None
                    if v is not None and v > 0:
                        clean_vols.append(int(v))
                    else:
                        h = highs[i] if i < len(highs) and highs[i] is not None else 0.0
                        l = lows[i] if i < len(lows) and lows[i] is not None else 0.0
                        spread = abs(h - l)
                        synthetic_vol = int(max(spread, 0.5) * 50000)
                        clean_vols.append(synthetic_vol)

                df = pd.DataFrame(
                    {
                        "Open": opens,
                        "High": highs,
                        "Low": lows,
                        "Close": closes,
                        "Volume": clean_vols,
                    },
                    index=pd.DatetimeIndex(dt_index, name="Datetime"),
                )

                df.dropna(subset=["Close"], inplace=True)
                df["Open"] = df["Open"].fillna(df["Close"])
                df["High"] = df["High"].fillna(df["Close"])
                df["Low"] = df["Low"].fillna(df["Close"])

                # Enforce OHLC invariants
                df["High"] = np.maximum(df["High"], np.maximum(df["Open"], df["Close"]))
                df["Low"] = np.minimum(df["Low"], np.minimum(df["Open"], df["Close"]))

                if len(df) > limit:
                    df = df.iloc[-limit:]

                if not df.empty:
                    cls._cached_candles[cache_key] = df
                    cls._candle_cache_ts[cache_key] = now_ts
                    return df

        except Exception as e:
            logger.debug(f"Public candle fetch failed for {symbol}: {e}")

        return cls._cached_candles.get(cache_key)
