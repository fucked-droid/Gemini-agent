# Live Indian Market Terminal — Production Build

A professional, institutional-grade Indian stock market monitoring terminal built in Python with synchronized CLI (Python Rich) and high-performance Web Single Page Application (FastAPI + WebSockets + HTML5).

---

## Architecture Overview

```
live-market-terminal/
├── web_server.py          # FastAPI/Uvicorn live WebSocket web server & SPA entry point
├── terminal.py            # Rich CLI terminal entry point
├── config.py              # Central configuration, credentials & schedule
├── requirements.txt       # Production dependencies
├── .env.example           # Environment variables template
├── static/                # Single Page Application (HTML, CSS, JS)
├── data/
│   ├── dhan_client.py     # DhanHQ REST API client with rate-limiting & backoff
│   ├── instrument_master.py # Scrip master downloader, cache & security ID resolver
│   ├── websocket_client.py # DhanHQ MarketFeed WebSocket tick streaming worker
│   ├── historical_data.py # Multi-timeframe resampling & OHLC invariant validator
│   └── market_cache.py    # Centralized thread-safe cache & snapshot store
├── analytics/
│   ├── indicators.py      # EMA 10/20, VWAP, RSI, MACD, ATR, Bollinger Bands, ORB
│   ├── order_flow.py      # CVD calculation, Delta decomposition, Buyer/Seller pressure
│   ├── market_structure.py # Fractal swing highs/lows, HH/LL, BOS & CHoCH events
│   ├── market_breadth.py  # NIFTY advance/decline ratio & verified institutional flow
│   └── multi_timeframe.py # Multi-timeframe alignment (1m, 5m, 15m, 30m, 60m)
├── prediction/
│   ├── features.py        # Strictly past-only feature extraction (zero lookahead)
│   ├── models.py          # Baseline quantitative momentum & directional classifier
│   ├── validation.py      # Walk-forward validation, Brier score, ECE & friction tests
│   └── forecasting.py     # Multi-horizon forecast orchestrator (5m, 15m, 30m, 60m)
├── signals/
│   ├── decision_engine.py # Rules-based BUY / SELL / WAIT decision engine
│   └── risk_management.py # Lot sizing, stop-loss distance & daily risk limits
└── tests/
    ├── test_indicators.py     # Mathematical verification of all technical indicators
    ├── test_market_data.py    # Dhan API parsing, instrument resolution, candle checks
    ├── test_order_flow_and_structure.py # CVD, Delta, Swings & BOS validation
    ├── test_decision_engine.py# BUY/SELL/WAIT signals & risk sizing tests
    ├── test_forecasting.py    # Model inference, walk-forward & Brier score tests
    └── test_cache_and_refresh.py # Thread-safe cache & disk snapshot tests
```

---

## Quick Startup Instructions

### 1. Environment Setup

```bash
# Clone or navigate to the workspace
cd live-market-terminal

# (Optional) Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Credentials (DhanHQ)

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` with your DhanHQ API credentials:
```env
DHAN_CLIENT_ID=your_client_id_here
DHAN_ACCESS_TOKEN=your_access_token_here
REFRESH_INTERVAL_SECONDS=30
```
> **Note:** If API credentials are not supplied, the terminal automatically runs in **Offline Historical / Simulation Mode** using official historical master datasets. It never claims mock data as live prices.

---

### 3. Launching the Interfaces

The application supports both root-level and directory-level execution:

#### Option A: Professional CLI Terminal (VS Code / Terminal)
```bash
# From workspace root:
python terminal.py

# Or with options:
python terminal.py --symbol NIFTY --interval 30
python terminal.py --once    # Single snapshot run
```

#### Option B: Institutional Browser Dashboard (Streamlit + Plotly)
```bash
# From workspace root:
streamlit run app.py

# Or from live-market-terminal:
cd live-market-terminal && streamlit run app.py
```
Open `http://localhost:8501` in your browser. Both interfaces automatically synchronize every 30 seconds via the shared `MarketCache`.

---

## Running the Automated Test Suite

To run all 31 unit and integration tests:
```bash
python live-market-terminal/run_tests.py
```
Or with pytest:
```bash
pytest live-market-terminal/tests/ -v
```

---

## Core Capabilities

1. **Exchange Awareness**: Automatically detects NSE schedule (Pre-Market, Live Session 09:15-15:30 IST, Post-Market, Closed, Weekend/Holiday).
2. **Order Flow & CVD**: Bar-level volume delta decomposition with Cumulative Volume Delta (CVD) tracking and buyer vs. seller pressure percentages.
3. **Multi-Timeframe Engine**: Analyzes 1m, 5m, 15m, 30m, and 60m timeframes for EMA stacking, VWAP position, and directional momentum.
4. **Predictive Models**: Generates 5m, 15m, 30m, and 60m directional forecasts with target ranges and out-of-sample walk-forward validation (Brier score & calibration gates).
5. **Rules-Based Decision Engine**: Clear `BUY`, `SELL`, or `WAIT` stance with Entry Zone, Stop-Loss, Targets (1.5R & 2.5R), Invalidation triggers, and full audit reasons.
