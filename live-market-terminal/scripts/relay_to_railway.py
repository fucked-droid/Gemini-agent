"""
Live Feed Relay to Production Cloud Terminal (Railway / Render).
Continuously bridges real-time market ticks, quotes, indicators, and signals
from the local execution engine directly into the deployed cloud website.
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("FeedRelay")

DEFAULT_RAILWAY_URL = os.getenv(
    "RAILWAY_URL", "https://gemini-agent-production-4247f579.up.railway.app"
).rstrip("/")

def fetch_local_snapshot(local_url: str = "http://127.0.0.1:8000") -> dict:
    """Fetches full state snapshot from local server running on port 8000."""
    try:
        req = urllib.request.Request(
            f"{local_url}/api/overview",
            headers={"User-Agent": "FeedRelay/1.0"},
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode())
            quotes = data.get("quotes", {})
            mkt_status = data.get("market_status", {})
            return {
                "quotes": quotes,
                "market_status": mkt_status,
                "source": "LOCAL_TERMINAL_PUMP",
            }
    except Exception:
        return None

def fetch_direct_ticks() -> dict:
    """Fetches real-time ticks directly using PublicNSEFeed and CryptoFeed."""
    quotes = {}
    for sym in ["NIFTY", "BANKNIFTY", "INDIAVIX"]:
        q = PublicNSEFeed.get_live_quote(sym)
        if q:
            quotes[sym] = q
    btc = CryptoFeed.get_live_quote("BTC")
    if btc:
        quotes["BTC"] = btc
    
    now_ist = get_ist_now()
    return {
        "quotes": quotes,
        "market_status": {
            "status": "LIVE",
            "phase": "REGULAR_SESSION",
            "is_open": True,
            "timestamp": now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
            "message": "Continuous trading hours (Relay Stream Active).",
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
                logger.info(
                    f"✓ Synced to Railway in {elapsed_ms:.0f}ms | NIFTY: ₹{price} ({chg:+.2f}, {pct:+.2f}%)"
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

def run_relay(target_url: str, interval: float = 3.0):
    """Main relay loop."""
    print("=" * 70)
    print("LIVE MARKET FEED RELAY -> RAILWAY PRODUCTION")
    print(f"Target URL : {target_url}")
    print(f"Sync Rate  : Every {interval}s")
    print("Press CTRL+C to stop.")
    print("=" * 70)

    consecutive_failures = 0
    while True:
        try:
            # 1. Try fetching from local server first, fallback to direct feed
            payload = fetch_local_snapshot()
            if not payload or not payload.get("quotes"):
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

        time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Feed Relay to Railway")
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
    args = parser.parse_args()
    run_relay(args.target, args.interval)
