"""
Public Real-Time NSE Option Chain Feed (NIFTY & BANKNIFTY).
Fetches live options data directly from NSE India (option-chain-v3 API)
with automatic session cookie negotiation, expiry resolution, in-memory caching,
and disk persistence.
"""

import os
import sys
import time
import json
import logging
import datetime
import http.cookiejar
import ssl
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from config import get_ist_now, CACHE_DIR

logger = logging.getLogger("NSEOptionChainFeed")

class NSEOptionChainFeed:
    """
    Authoritative live option chain data fetcher for NSE indices.
    """

    PRIMARY_HOST = "https://www.nseindia.in"
    SECONDARY_HOST = "https://www.nseindia.com"

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )

    PAGE_HEADERS = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
    }

    API_HEADERS = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }

    _cookie_jar: Optional[http.cookiejar.CookieJar] = None
    _opener: Optional[urllib.request.OpenerDirector] = None
    _last_handshake_time: float = 0.0
    _handshake_ttl: float = 300.0  # Re-handshake cookies every 5 minutes

    _mem_cache: Dict[str, Dict[str, Any]] = {}
    _cache_timestamps: Dict[str, float] = {}
    CACHE_TTL: float = 45.0  # Keep options data cached in memory for 45 seconds

    @classmethod
    def _get_opener(cls) -> urllib.request.OpenerDirector:
        """Initializes or returns HTTP opener with SSL context and CookieJar."""
        if cls._opener is None:
            cls._cookie_jar = http.cookiejar.CookieJar()
            ctx = ssl.create_default_context()
            ctx.set_ciphers("DEFAULT@SECLEVEL=1")
            cls._opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(cls._cookie_jar),
                urllib.request.HTTPSHandler(context=ctx),
            )
        return cls._opener

    @classmethod
    def _perform_handshake(cls, host: str = PRIMARY_HOST) -> bool:
        """Visits option-chain page to collect session tracking cookies."""
        now = time.time()
        if (now - cls._last_handshake_time) < cls._handshake_ttl and cls._cookie_jar and len(cls._cookie_jar) > 0:
            return True

        opener = cls._get_opener()
        page_url = f"{host}/option-chain"
        headers = dict(cls.PAGE_HEADERS)
        headers["Referer"] = f"{host}/"

        try:
            req = urllib.request.Request(page_url, headers=headers)
            with opener.open(req, timeout=8.0) as resp:
                if resp.status == 200:
                    cls._last_handshake_time = time.time()
                    logger.debug(f"NSE handshake successful on {host}. Cookies: {len(cls._cookie_jar)}")
                    return True
        except Exception as e:
            logger.warning(f"Handshake failed on {host}: {e}")

        return False

    @classmethod
    def fetch_live_chain(cls, symbol: str = "NIFTY") -> Optional[Dict[str, Any]]:
        """
        Fetches live option chain from NSE option-chain-v3 endpoint.
        Returns parsed JSON dictionary or None on failure.
        """
        sym = symbol.upper()
        now = time.time()

        # Check in-memory TTL
        if sym in cls._mem_cache and (now - cls._cache_timestamps.get(sym, 0.0)) < cls.CACHE_TTL:
            return cls._mem_cache[sym]

        opener = cls._get_opener()

        for host in [cls.PRIMARY_HOST, cls.SECONDARY_HOST]:
            try:
                # Step 1: Ensure session cookies are present
                if not cls._perform_handshake(host):
                    continue

                time.sleep(0.3)

                # Step 2: Fetch contract info for active expiry dates
                contract_url = f"{host}/api/option-chain-contract-info?symbol={urllib.parse.quote(sym)}"
                api_headers = dict(cls.API_HEADERS)
                api_headers["Referer"] = f"{host}/option-chain"

                req_contract = urllib.request.Request(contract_url, headers=api_headers)
                contract_data = None
                with opener.open(req_contract, timeout=8.0) as resp:
                    if resp.status == 200:
                        contract_data = json.loads(resp.read().decode("utf-8"))

                if not contract_data or not contract_data.get("expiryDates"):
                    continue

                active_expiry = contract_data["expiryDates"][0]

                time.sleep(0.3)

                # Step 3: Fetch option-chain-v3 with nearest active expiry
                v3_url = (
                    f"{host}/api/option-chain-v3?type=Indices&symbol={urllib.parse.quote(sym)}"
                    f"&expiry={urllib.parse.quote(active_expiry)}"
                )
                req_v3 = urllib.request.Request(v3_url, headers=api_headers)
                with opener.open(req_v3, timeout=10.0) as resp:
                    if resp.status == 200:
                        raw_json = json.loads(resp.read().decode("utf-8"))
                        records = raw_json.get("records", {})
                        if records and records.get("data"):
                            # Ensure expiryDates list is attached for downstream processing
                            if "expiryDates" not in records or not records["expiryDates"]:
                                records["expiryDates"] = contract_data.get("expiryDates", [])

                            # Update memory cache
                            cls._mem_cache[sym] = raw_json
                            cls._cache_timestamps[sym] = time.time()

                            # Persist to disk cache
                            cls._save_to_disk_cache(sym, raw_json)
                            logger.info(
                                f"Successfully fetched live {sym} option chain (Underlying: "
                                f"{records.get('underlyingValue')}, Expiry: {active_expiry})"
                            )
                            return raw_json

            except Exception as e:
                logger.warning(f"Error fetching option chain for {sym} from {host}: {e}")

        # If live fetch failed, attempt to return disk cache
        return cls._load_disk_cache(sym)

    @classmethod
    def _save_to_disk_cache(cls, symbol: str, data: Dict[str, Any]):
        """Persists option chain JSON to cache directory."""
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file = CACHE_DIR / f"option_chain_{symbol.lower()}.json"
            temp_file = CACHE_DIR / f"option_chain_{symbol.lower()}.tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            temp_file.replace(cache_file)
        except Exception as e:
            logger.warning(f"Failed to save disk cache for {symbol}: {e}")

    @classmethod
    def _load_disk_cache(cls, symbol: str) -> Optional[Dict[str, Any]]:
        """Loads cached option chain JSON from disk."""
        cache_file = CACHE_DIR / f"option_chain_{symbol.lower()}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cls._mem_cache[symbol.upper()] = data
                    cls._cache_timestamps[symbol.upper()] = time.time()
                    return data
            except Exception as e:
                logger.warning(f"Failed to read disk cache for {symbol}: {e}")
        return None

    @classmethod
    def refresh_all(cls, symbols: Optional[List[str]] = None) -> Dict[str, bool]:
        """Refreshes option chains for monitored symbols."""
        target_symbols = symbols or ["NIFTY", "BANKNIFTY"]
        results = {}
        for sym in target_symbols:
            data = cls.fetch_live_chain(sym)
            results[sym] = (data is not None)
        return results
