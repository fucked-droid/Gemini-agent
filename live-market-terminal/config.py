"""
Centralized Configuration Module for Live Indian Market Terminal.
Handles environment variables, DhanHQ API endpoints, trading schedules,
indicator parameters, and logging configuration.
"""

import os
import sys
import datetime
from pathlib import Path
from dotenv import load_dotenv

# Indian Standard Time (IST) Timezone Definition (UTC+5:30)
IST_TZ = datetime.timezone(datetime.timedelta(hours=5, minutes=30), name="IST")

def get_ist_now() -> datetime.datetime:
    """Returns current datetime in Indian Standard Time (IST, UTC+5:30)."""
    return datetime.datetime.now(IST_TZ)


# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = PROJECT_ROOT.parent

# Load environment variables (.env in live-market-terminal or parent workspace)
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(WORKSPACE_ROOT / ".env")

# DhanHQ Credentials
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "")

# API Endpoints & URLs
DHAN_BASE_URL = os.getenv("DHAN_BASE_URL", "https://api.dhan.co/v2")
DHAN_WSS_URL = os.getenv("DHAN_WSS_URL", "wss://api-feed.dhan.co")
DHAN_SCRIP_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"

# Cache & Storage Directories
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
SCRIP_MASTER_CACHE_FILE = CACHE_DIR / "api-scrip-master.csv"
MARKET_STATE_SNAPSHOT_FILE = CACHE_DIR / "market_snapshot.json"

# Refresh & Polling Parameters
DEFAULT_REFRESH_INTERVAL_SECONDS = int(os.getenv("REFRESH_INTERVAL_SECONDS", "30"))
API_RATE_LIMIT_DELAY = float(os.getenv("API_RATE_LIMIT_DELAY", "0.2"))  # max 5-10 req/s
MAX_API_RETRIES = int(os.getenv("MAX_API_RETRIES", "3"))
BACKOFF_FACTOR = float(os.getenv("BACKOFF_FACTOR", "1.5"))

# Monitored Instruments
MONITORED_INSTRUMENTS = {
    "NIFTY": {
        "symbol": "NIFTY",
        "name": "NIFTY 50",
        "exchange": "NSE_INDEX",
        "segment": "IDX",
        "security_id": "13",
        "lot_size": 25,
        "tick_size": 0.05,
    },
    "BANKNIFTY": {
        "symbol": "BANKNIFTY",
        "name": "NIFTY BANK",
        "exchange": "NSE_INDEX",
        "segment": "IDX",
        "security_id": "25",
        "lot_size": 15,
        "tick_size": 0.05,
    },
    "INDIAVIX": {
        "symbol": "INDIAVIX",
        "name": "INDIA VIX",
        "exchange": "NSE_INDEX",
        "segment": "IDX",
        "security_id": "24",
        "lot_size": 1,
        "tick_size": 0.01,
    },
    "BTC": {
        "symbol": "BTC",
        "name": "Bitcoin (BTC/USD 24/7)",
        "exchange": "CRYPTO_24_7",
        "segment": "CRYPTO",
        "security_id": "BTCUSD",
        "lot_size": 1,
        "tick_size": 0.1,
        "currency": "$",
    },
}

# Top NIFTY Constituents for Breadth & Heavyweight Tracking
TOP_NIFTY_CONSTITUENTS = [
    {"symbol": "RELIANCE", "name": "Reliance Industries", "weight": 9.2, "security_id": "2885"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "weight": 11.5, "security_id": "1333"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "weight": 8.1, "security_id": "4963"},
    {"symbol": "INFY", "name": "Infosys Ltd", "weight": 5.8, "security_id": "1594"},
    {"symbol": "TCS", "name": "Tata Consultancy Services", "weight": 4.1, "security_id": "11536"},
    {"symbol": "ITC", "name": "ITC Ltd", "weight": 3.9, "security_id": "1660"},
    {"symbol": "LT", "name": "Larsen & Toubro Ltd", "weight": 3.7, "security_id": "11483"},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank", "weight": 2.8, "security_id": "1922"},
    {"symbol": "AXISBANK", "name": "Axis Bank Ltd", "weight": 3.2, "security_id": "5900"},
    {"symbol": "SBIN", "name": "State Bank of India", "weight": 2.9, "security_id": "3045"},
]

# Supported Multi-Timeframes (minutes)
SUPPORTED_TIMEFRAMES = ["1m", "5m", "15m", "30m", "60m"]
PREDICTION_HORIZONS = ["5m", "15m", "30m", "60m"]

# Technical Indicator Defaults
INDICATOR_PARAMS = {
    "ema_fast": 10,
    "ema_slow": 20,
    "rsi_period": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "atr_period": 14,
    "bollinger_period": 20,
    "bollinger_std": 2.0,
    "opening_range_minutes": 15,
}

# Market Session Timings (IST)
SESSION_TIMINGS = {
    "pre_market_start": (9, 0),
    "pre_market_end": (9, 15),
    "market_open": (9, 15),
    "market_close": (15, 30),
    "post_market_end": (16, 0),
}

# Logging configuration
import logging

LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "terminal.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("LiveMarketTerminal")
