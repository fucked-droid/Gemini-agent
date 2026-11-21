"""
Live Feed Relay to Production Cloud Terminal (Railway / Render).
Continuously bridges real-time market ticks, quotes, indicators, and signals
AND live option chain feeds from the local execution engine directly into the deployed cloud website.
"""

import os
import sys
import time
import json
import logging
import argparse
from pathlib import Path
import urllib.request
import urllib.error

# Add live-market-terminal to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import get_ist_now
from data.public_nse_feed import PublicNSEFeed
from data.crypto_feed import CryptoFeed
from data.options_feed import NSEOptionChainFeed
from analytics.options_analytics import OptionsAnalytics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("FeedRelay")

DEFAULT_RAILWAY_URL = os.getenv(
    "RAILWAY_URL", "https://gemini-agent-production-4247f579.up.railway.app"
).rstrip("/")

# Cached state for options relay
_last_options_fetch_time = 0.0
_cached_options_analytics = {}
_cached_options_chains = {}
OPTIONS_REFRESH_INTERVAL = 15.0  # Fetch options data every 15 seconds

def fetch_options_data(quotes: dict) -> tuple:
    """
    Fetches real-time NSE Option Chain data and computes quantitative options intelligence.
    Caches results and refreshes every OPTIONS_REFRESH_INTERVAL seconds.
    """
    global _last_options_fetch_time, _cached_options_analytics, _cached_options_chains
    now = time.time()

    if _cached_options_analytics and (now - _last_options_fetch_time) < OPTIONS_REFRESH_INTERVAL:
        return _cached_options_analytics, _cached_options_chains

    analytics = {}
    chains = {}

    for sym in ["NIFTY", "BANKNIFTY"]:
        try:
            spot = float(quotes.get(sym, {}).get("price", 0.0) or 0.0)
            chain = NSEOptionChainFeed.fetch_live_chain(sym)
            if chain:
                chains[sym] = chain
                opt_intel = OptionsAnalytics.get_options_intelligence(sym, spot_price=spot, allow_sample=True)
                analytics[sym] = {
                    "options_intelligence": opt_intel,
                    "market_intelligence": {
                        "options_sentiment": opt_intel.get("sentiment", "Unavailable"),
                        "options_details": opt_intel.get("details", ""),
                        "options_pcr": opt_intel.get("pcr_oi"),
                    }
                }
                logger.info(f"Updated live {sym} options: PCR {opt_intel.get('pcr_oi')} | Max Pain {opt_intel.get('max_pain')} | Sentiment: {opt_intel.get('sentiment')}")
        except Exception as e:
            logger.warning(f"Error resolving options for {sym}: {e}")

    if analytics:
        _cached_options_analytics = analytics
        _cached_options_chains = chains
        _last_options_fetch_time = now

    return _cached_options_analytics, _cached_options_chains

def fetch_direct_ticks() -> dict:
    """Fetches real-time ticks directly using PublicNSEFeed, CryptoFeed, and NSEOptionChainFeed."""
    quotes = {}
    for sym in ["NIFTY", "BANKNIFTY", "INDIAVIX"]:
        try:
            q = PublicNSEFeed.get_live_quote(sym)
            if q:
                quotes[sym] = q
        except Exception as qe:
            logger.debug(f"Quote fetch error for {sym}: {qe}")

    try:
        # Only Indian market quotes forwarded
    except Exception as ce:
        logger.debug(f"Crypto fetch error: {ce}")

    now_ist = get_ist_now()
    analytics, chains = fetch_options_data(quotes)

    return {
        "quotes": quotes,
        "analytics": analytics,
        "options_chain": chains,
        "market_status": {
            "status": "LIVE",
            "phase": "REGULAR_SESSION",
            "is_open": True,
            "timestamp": now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
            "message": "Continuous trading hours (Relay Stream Active with Live Option Feed).",
        },
        "source": "DIRECT_NSE_PUBLIC_RELAY",
    }

def push_to_cloud(target_url: str, payload: dict) -> bool:
    """Pushes market data packet to Railway endpoint."""
    sync_url = f"{target_url}/api/feed/sync"
    data_bytes = json.dumps(payload, default=str).encode("utf-8")
    req = urllib.request.Request(
        sync_url,
        data=data_bytes,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "LiveFeedRelay/1.0",
        },
        method="POST",
    )
    start_t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            elapsed_ms = (time.time() - start_t) * 1000.0
            if resp.status == 200:
                nifty_quote = payload.get("quotes", {}).get("NIFTY", {})
                price = nifty_quote.get("price", "N/A")
                chg = nifty_quote.get("change", 0.0)
                pct = nifty_quote.get("change_pct", 0.0)
                nifty_opt = payload.get("analytics", {}).get("NIFTY", {}).get("options_intelligence", {})
                pcr = nifty_opt.get("pcr_oi", "N/A")
                opt_sent = nifty_opt.get("sentiment", "N/A")
                logger.info(
                    f"✓ Synced to Railway in {elapsed_ms:.0f}ms | NIFTY: ₹{price} ({chg:+.2f}, {pct:+.2f}%) | Options PCR: {pcr} ({opt_sent})"
                )
                return True
            else:
                logger.warning(f"Railway returned status {resp.status}")
                return False
    except urllib.error.HTTPError as he:
        if he.code == 404:
            logger.error(
                f"Endpoint {sync_url} returned 404. Railway needs to be redeployed with the latest code."
            )
        else:
            logger.error(f"HTTP Error {he.code}: {he.reason}")
        return False
    except Exception as e:
        logger.error(f"Sync error: {e}")
        return False

def run_relay(target_url: str, interval: float = 3.0, once: bool = False):
    """Main relay loop."""
    print("=" * 70)
    print("LIVE MARKET FEED & OPTION DATA RELAY -> RAILWAY PRODUCTION")
    print(f"Target URL : {target_url}")
    print(f"Sync Rate  : Every {interval}s")
    print("Press CTRL+C to stop.")
    print("=" * 70)

    consecutive_failures = 0
    while True:
        try:
            payload = fetch_direct_ticks()

            if payload and payload.get("quotes"):
                success = push_to_cloud(target_url, payload)
                if success:
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
            else:
                logger.warning("No quotes available to sync.")

        except KeyboardInterrupt:
            print("\nRelay stopped by user.")
            break
        except Exception as e:
            logger.error(f"Unexpected relay loop error: {e}")

        if once:
            break

        time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Feed & Options Relay to Railway")
    parser.add_argument(
        "--target",
        default=DEFAULT_RAILWAY_URL,
        help="Target cloud website URL",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=3.0,
        help="Sync interval in seconds",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run single sync iteration and exit",
    )
    args = parser.parse_args()
    run_relay(args.target, args.interval, args.once)
