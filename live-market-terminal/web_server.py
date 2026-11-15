"""
Live Indian Market Terminal — High-Performance Web Server.
Built with FastAPI, Uvicorn, and WebSockets.
Provides continuous live tick broadcasting, REST APIs, and serves the browser SPA.
"""

import os
import sys
import time
import json
import asyncio
import datetime
import logging
from pathlib import Path
from typing import Dict, Any, List, Set, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import pandas as pd
import numpy as np

# Ensure live-market-terminal is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    DEFAULT_REFRESH_INTERVAL_SECONDS,
    MONITORED_INSTRUMENTS,
    TOP_NIFTY_CONSTITUENTS,
)
from data import (
    DhanClient,
    HistoricalDataManager,
    get_global_cache,
    get_market_status_manager,
    MarketDataStatus,
)
from analytics import (
    TechnicalIndicators,
    OrderFlowAnalyzer,
    MarketStructureAnalyzer,
    MarketBreadthAnalyzer,
    MultiTimeframeEngine,
    OptionsAnalytics,
    PerformanceAnalytics,
    SMCAnalyzer,
)
from prediction import ForecastOrchestrator
from signals import TradingDecisionEngine

logger = logging.getLogger("WebTerminalServer")

app = FastAPI(
    title="Live Indian Market Terminal Web API",
    description="Real-time market analytics, order flow, predictive forecasts, and trading decisions.",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files directory
STATIC_DIR = PROJECT_ROOT / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# State & WebSocket Connection Manager
class ConnectionManager:
    """Manages active browser WebSocket connections for live broadcasting."""
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        dead_connections = set()
        msg_text = json.dumps(message, default=str)
        for connection in self.active_connections:
            try:
                await connection.send_text(msg_text)
            except Exception:
                dead_connections.add(connection)
        for dead in dead_connections:
            self.active_connections.discard(dead)

manager = ConnectionManager()
client = DhanClient()
cache = get_global_cache()

def process_symbol_pipeline(sym: str, quote: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Executes the complete multi-source analytics and signal decision pipeline for an instrument.
    Caches the results in MarketCache and returns the decision dictionary.
    """
    if quote is None:
        quote = client.get_quote(sym)
        cache.update_quote(sym, quote)

    candles_1m = client.get_historical_candles(sym, interval="1m", days=3)
    tf_suite = HistoricalDataManager.build_timeframe_suite(candles_1m)
    cache.set_candles(sym, tf_suite)

    candles_5m = tf_suite.get("5m", candles_1m)
    df_enriched, ind_sc = TechnicalIndicators.calculate_all(candles_5m)
    order_flow = OrderFlowAnalyzer.analyze_order_flow(candles_5m, session_df=candles_1m)
    structure = MarketStructureAnalyzer.analyze_structure(candles_5m)
    smc_analysis = SMCAnalyzer.analyze_smc(candles_5m)

    # Strict Instrument Data Isolation: Do not allow BTC data or crypto logic into NIFTY/BANKNIFTY calculations
    if sym == "BTC":
        breadth = {
            "status": "NOT_APPLICABLE",
            "advances": 0,
            "declines": 0,
            "adr": 1.0,
            "breadth_score": 0.0,
            "interpretation": "Global 24/7 Crypto Flow (NSE Breadth N/A)",
        }
        inst_flow = {
            "status": "NOT_APPLICABLE",
            "net_flow_cr": 0.0,
            "interpretation": "Digital Assets 24/7 Spot / Perpetual Market",
        }
    else:
        breadth = MarketBreadthAnalyzer.compute_breadth_from_constituents(TOP_NIFTY_CONSTITUENTS)
        inst_flow = MarketBreadthAnalyzer.get_institutional_flow()

    mtf_data = MultiTimeframeEngine.evaluate_multi_timeframe_suite(tf_suite)

    spot = quote.get("price", 25144.30 if sym != "BTC" else 65850.0)
    atr = ind_sc.get("atr", spot * 0.005)
    forecasts = ForecastOrchestrator.run_prediction_pipeline(df_enriched, spot, atr)

    decision = TradingDecisionEngine.evaluate(
        spot_price=spot,
        indicators=ind_sc,
        mtf_data=mtf_data,
        order_flow=order_flow,
        market_structure=structure,
        market_breadth=breadth,
        buy_priority_mode=True,
        smc_data=smc_analysis,
    )

    # Market Intelligence Synthesis
    struct_state = structure.get("structure_state", "NEUTRAL")
    if "BULLISH" in struct_state:
        ms_label = "Bullish"
    elif "BEARISH" in struct_state:
        ms_label = "Bearish"
    else:
        ms_label = "Neutral"

    vwap_val = float(ind_sc.get("vwap", spot))
    if vwap_val > 0:
        diff_pct = (spot - vwap_val) / vwap_val
        if diff_pct > 0.0005:
            vwap_pos = "Above VWAP"
        elif diff_pct < -0.0005:
            vwap_pos = "Below VWAP"
        else:
            vwap_pos = "At VWAP"
    else:
        vwap_pos = "At VWAP"

    buyer_pct = float(order_flow.get("buyer_percentage", 50.0))
    flow_state = order_flow.get("order_flow_state", "NEUTRAL")
    if buyer_pct >= 52.0 or "BUYING" in flow_state:
        of_label = "Buyers Dominating"
    elif buyer_pct <= 48.0 or "SELLING" in flow_state:
        of_label = "Sellers Dominating"
    else:
        of_label = "Balanced"

    opt_analysis = OptionsAnalytics.get_options_intelligence(sym, spot)
    opt_sentiment = opt_analysis.get("sentiment", "Unavailable")
    perf_metrics = PerformanceAnalytics.get_performance_metrics(sym)

    status_mgr = get_market_status_manager()
    status_info = status_mgr.get_status(sym)

    # Shared CVD value anchored to session open for complete cross-component parity
    shared_session_cvd = order_flow.get("session_cvd", order_flow.get("cvd", 0))

    market_intelligence = {
        "market_structure": ms_label,
        "vwap_position": vwap_pos,
        "vwap_value": round(vwap_val, 2),
        "order_flow": of_label,
        "buyer_percentage": round(buyer_pct, 1),
        "cvd": shared_session_cvd,
        "session_cvd": shared_session_cvd,
        "timeframe_cvd": order_flow.get("timeframe_cvd", 0),
        "candle_delta": order_flow.get("candle_delta", 0),
        "options_sentiment": opt_sentiment,
        "options_details": opt_analysis.get("details", ""),
        "options_pcr": opt_analysis.get("pcr_oi"),
        "data_status": status_info,
    }

    # Attach market intelligence to decision payload
    decision["market_intelligence"] = market_intelligence

    # Store serializable analytics in cache
    cache.update_analytics(sym, {
        "indicators": ind_sc,
        "order_flow": {k: v for k, v in order_flow.items() if k != "df_with_cvd"},
        "market_structure": structure,
        "smc": smc_analysis,
        "options_intelligence": opt_analysis,
        "performance": perf_metrics,
        "market_breadth": breadth,
        "institutional_flow": inst_flow,
        "mtf": mtf_data,
        "market_intelligence": market_intelligence,
    })
    cache.update_forecasts(sym, forecasts)
    cache.update_signals(sym, decision)

    return decision

# Background monitoring loop
async def continuous_market_monitor_task():
    """
    Background worker: continuously updates market data, executes analytics pipeline,
    and broadcasts live updates over WebSockets every few seconds.
    """
    logger.info("Continuous Market Monitoring Worker started.")
    while True:
        try:
            # 1. Update Market Session Status
            market_status = client.get_market_status()
            cache.update_market_status(market_status)

            # 2. Update Quotes for Monitored Instruments
            quotes = {}
            for sym in MONITORED_INSTRUMENTS:
                q = client.get_quote(sym)
                quotes[sym] = q
                cache.update_quote(sym, q)

            # 3. Process NIFTY, BANKNIFTY, and Bitcoin (24/7 Live Data)
            for sym in ["NIFTY", "BANKNIFTY", "BTC"]:
                process_symbol_pipeline(sym, quotes.get(sym))

            api_state = "LIVE_AUTHENTICATED" if client.is_authenticated else "OFFLINE_SIMULATION"
            cache.update_system_status(api_state, "Continuous market stream active.")
            cache.save_to_snapshot()

            status_mgr = get_market_status_manager()
            market_data_status = {
                "NIFTY": status_mgr.get_status("NIFTY"),
                "BANKNIFTY": status_mgr.get_status("BANKNIFTY"),
                "BTC": status_mgr.get_status("BTC"),
            }

            # Broadcast live packet to all connected web clients
            packet = {
                "type": "TICK_UPDATE",
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
                "quotes": quotes,
                "market_status": market_status,
                "market_data_status": market_data_status,
                "active_symbol": "NIFTY",
                "analytics": cache.analytics.get("NIFTY", {}),
                "forecasts": cache.forecasts.get("NIFTY", {}),
                "signals": cache.signals.get("NIFTY", {}),
                "analytics_by_symbol": cache.analytics,
                "forecasts_by_symbol": cache.forecasts,
                "signals_by_symbol": cache.signals,
                "system_status": cache.system_status,
            }
            await manager.broadcast(packet)

        except Exception as e:
            logger.error(f"Error in continuous market monitor: {e}")

        # Continuous tick interval: 3 seconds for responsive web terminal
        await asyncio.sleep(3.0)

@app.on_event("startup")
async def startup_event():
    """Starts background monitor on server boot."""
    if os.getenv("TESTING", "0") != "1":
        asyncio.create_task(continuous_market_monitor_task())

# ==========================================
# REST API ENDPOINTS
# ==========================================

@app.get("/")
def serve_index():
    """Serves the main single-page web terminal interface."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h2>Live Indian Market Terminal</h2><p>Static index.html loading...</p>")

@app.get("/api/overview")
def get_overview():
    """Returns quotes, exchange clock, market status, and authoritative feed status."""
    snap = cache.get_snapshot()
    status_mgr = get_market_status_manager()
    return {
        "quotes": snap.get("quotes", {}),
        "market_status": snap.get("market_status", {}),
        "market_data_status": {
            "NIFTY": status_mgr.get_status("NIFTY"),
            "BANKNIFTY": status_mgr.get_status("BANKNIFTY"),
            "BTC": status_mgr.get_status("BTC"),
        },
        "system_status": snap.get("system_status", {}),
    }

@app.get("/api/candles")
def get_candles(symbol: str = "NIFTY", timeframe: str = "5m"):
    """
    Returns chart-ready OHLCV candle bars and indicator series for the specified timeframe.
    """
    sym = symbol.upper()
    tf = timeframe.lower()
    df_raw = cache.get_candles(sym, tf)

    if df_raw is None or df_raw.empty:
        # Fallback fetch
        df_1m = client.get_historical_candles(sym, interval="1m", days=2)
        suite = HistoricalDataManager.build_timeframe_suite(df_1m)
        cache.set_candles(sym, suite)
        df_raw = suite.get(tf, df_1m)

    df_enriched, _ = TechnicalIndicators.calculate_all(df_raw)
    order_flow = OrderFlowAnalyzer.compute_volume_delta(df_raw)

    bars = []
    for idx, row in df_enriched.iterrows():
        t_str = str(idx)
        cvd_val = int(order_flow.loc[idx, "CVD"]) if idx in order_flow.index else 0
        bars.append({
            "time": t_str,
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
            "ema10": round(float(row["EMA10"]), 2) if not pd.isna(row["EMA10"]) else None,
            "ema20": round(float(row["EMA20"]), 2) if not pd.isna(row["EMA20"]) else None,
            "vwap": round(float(row["VWAP"]), 2) if not pd.isna(row["VWAP"]) else None,
            "cvd": cvd_val,
        })

    return {
        "symbol": sym,
        "timeframe": tf,
        "count": len(bars),
        "bars": bars,
    }

@app.get("/api/internals")
def get_internals(symbol: str = "NIFTY"):
    """Returns order flow, CVD, market structure, breadth, and institutional flow."""
    sym = symbol.upper()
    if sym not in cache.analytics or not cache.analytics[sym] or "market_intelligence" not in cache.analytics[sym]:
        process_symbol_pipeline(sym)
    return cache.analytics.get(sym, {})

@app.get("/api/decision")
def get_decision(symbol: str = "NIFTY"):
    """Returns BUY / SELL / WAIT trading decision and playbook."""
    sym = symbol.upper()
    if sym not in cache.signals or not cache.signals[sym] or "clean_recommendation" not in cache.signals[sym]:
        process_symbol_pipeline(sym)
    return cache.signals.get(sym, {})

@app.get("/api/forecasts")
def get_forecasts(symbol: str = "NIFTY"):
    """Returns multi-horizon directional forecasts."""
    sym = symbol.upper()
    if sym not in cache.forecasts or not cache.forecasts[sym]:
        process_symbol_pipeline(sym)
    return cache.forecasts.get(sym, {})

@app.get("/api/options")
def get_options(symbol: str = "NIFTY"):
    """Returns Put-Call Ratio, Open Interest shifts, Max Pain, and strike radar."""
    sym = symbol.upper()
    if sym not in cache.analytics or not cache.analytics[sym] or "options_intelligence" not in cache.analytics[sym]:
        process_symbol_pipeline(sym)
    analytics_data = cache.analytics.get(sym, {})
    return analytics_data.get("options_intelligence", OptionsAnalytics.get_options_intelligence(sym))

@app.get("/api/performance")
def get_performance(symbol: str = "NIFTY"):
    """Returns historical accuracy, win rate, average R:R, max drawdown, and false signal rate."""
    sym = symbol.upper()
    if sym not in cache.analytics or not cache.analytics[sym] or "performance" not in cache.analytics[sym]:
        process_symbol_pipeline(sym)
    analytics_data = cache.analytics.get(sym, {})
    return analytics_data.get("performance", PerformanceAnalytics.get_performance_metrics(sym))

@app.get("/api/smc")
def get_smc(symbol: str = "NIFTY"):
    """Returns Smart Money Concepts (BOS, CHoCH, Liquidity Sweeps, Order Blocks, FVGs)."""
    sym = symbol.upper()
    if sym not in cache.analytics or not cache.analytics[sym] or "smc" not in cache.analytics[sym]:
        process_symbol_pipeline(sym)
    analytics_data = cache.analytics.get(sym, {})
    return analytics_data.get("smc", {})

@app.get("/api/orderflow")
def get_orderflow(symbol: str = "NIFTY"):
    """Returns order flow, CVD, Volume Profile (POC/VAH/VAL), and VWAP bands."""
    sym = symbol.upper()
    if sym not in cache.analytics or not cache.analytics[sym] or "order_flow" not in cache.analytics[sym]:
        process_symbol_pipeline(sym)
    analytics_data = cache.analytics.get(sym, {})
    return analytics_data.get("order_flow", {})

@app.get("/api/health")
def get_health():
    """Returns API health, data freshness, and active connections."""
    snap = cache.get_snapshot()
    return {
        "status": "HEALTHY",
        "active_clients": len(manager.active_connections),
        "system_status": snap.get("system_status", {}),
    }

# ==========================================
# WEBSOCKET STREAMING ENDPOINT
# ==========================================

@app.websocket("/ws/live")
async def websocket_live_stream(websocket: WebSocket):
    """
    Continuous WebSocket feed streaming real-time market ticks,
    indicators, and trading signals directly to browser clients.
    """
    await manager.connect(websocket)
    try:
        # Send initial snapshot immediately upon connection
        snap = cache.get_snapshot()
        status_mgr = get_market_status_manager()
        market_data_status = {
            "NIFTY": status_mgr.get_status("NIFTY"),
            "BANKNIFTY": status_mgr.get_status("BANKNIFTY"),
            "BTC": status_mgr.get_status("BTC"),
        }
        init_packet = {
            "type": "INITIAL_STATE",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
            "quotes": snap.get("quotes", {}),
            "market_status": snap.get("market_status", {}),
            "market_data_status": market_data_status,
            "active_symbol": "NIFTY",
            "analytics": cache.analytics.get("NIFTY", {}),
            "forecasts": cache.forecasts.get("NIFTY", {}),
            "signals": cache.signals.get("NIFTY", {}),
            "analytics_by_symbol": cache.analytics,
            "forecasts_by_symbol": cache.forecasts,
            "signals_by_symbol": cache.signals,
            "system_status": snap.get("system_status", {}),
        }
        await websocket.send_text(json.dumps(init_packet, default=str))

        # Keep connection open and listen for client commands (e.g. switch symbol)
        while True:
            data = await websocket.receive_text()
            try:
                cmd = json.loads(data)
                if cmd.get("action") == "PING":
                    await websocket.send_text(json.dumps({"type": "PONG", "time": time.time()}))
            except Exception:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.debug(f"WebSocket client error: {e}")
        manager.disconnect(websocket)

def run_server(port: int = 8000, host: str = "0.0.0.0"):
    """Runs Uvicorn web server."""
    uvicorn.run("web_server:app", host=host, port=port, log_level="info")

if __name__ == "__main__":
    run_server()
