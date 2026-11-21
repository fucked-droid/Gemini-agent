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
    get_ist_now,
    IST_TZ,
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
    MarketRegimeDetector,
    NewsAndEventRiskEngine,
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
    if "daily" not in tf_suite:
        daily_candles = client.get_historical_candles(sym, interval="1d", days=60)
        if daily_candles is not None and not daily_candles.empty:
            tf_suite["daily"] = daily_candles
    cache.set_candles(sym, tf_suite)

    candles_5m = tf_suite.get("5m", candles_1m)
    df_enriched, ind_sc = TechnicalIndicators.calculate_all(candles_5m)
    order_flow = OrderFlowAnalyzer.analyze_order_flow(candles_5m, session_df=candles_1m)

    # Real-Time NIFTY Futures Integration (Requirement 3: VWAP, CVD, Buyer/Seller Pressure)
    if sym == "NIFTY":
        try:
            from data.angel_provider import get_angel_provider
            fut_metrics = get_angel_provider().get_futures_metrics()
            if fut_metrics:
                if fut_metrics.get("vwap", 0) > 0:
                    ind_sc["vwap"] = fut_metrics["vwap"]
                if fut_metrics.get("buyer_percentage") is not None:
                    order_flow["buyer_percentage"] = fut_metrics["buyer_percentage"]
                if fut_metrics.get("session_cvd") is not None:
                    order_flow["session_cvd"] = fut_metrics["session_cvd"]
                    order_flow["cvd"] = fut_metrics["cvd"]
                    order_flow["is_cvd_available"] = True
                    order_flow["cvd_display"] = f"{fut_metrics['cvd']} contracts"
                order_flow["nifty_future_contract"] = fut_metrics.get("contract", "")
                order_flow["future_price"] = fut_metrics.get("fut_price", 0.0)
        except Exception as fe:
            logger.debug(f"Could not merge futures metrics: {fe}")

    structure = MarketStructureAnalyzer.analyze_structure(candles_5m)
    smc_analysis = SMCAnalyzer.analyze_smc(candles_5m)

    breadth = MarketBreadthAnalyzer.compute_breadth_from_constituents(TOP_NIFTY_CONSTITUENTS)
    inst_flow = MarketBreadthAnalyzer.get_institutional_flow()

    mtf_data = MultiTimeframeEngine.evaluate_multi_timeframe_suite(tf_suite)

    spot = quote.get("price", 25144.30)
    atr = ind_sc.get("atr", spot * 0.005)
    forecasts = ForecastOrchestrator.run_prediction_pipeline(df_enriched, spot, atr)

    status_mgr = get_market_status_manager()
    status_info = status_mgr.get_status(sym)

    # 4-Tier Institutional Multi-Timeframe Analysis (5m, 15m, 1h, daily)
    inst_4tf = MultiTimeframeEngine.institutional_4tf(tf_suite, spot_price=spot)

    # Market Regime & Volatility Analysis
    vix_quote = client.get_quote("INDIAVIX")
    vix_val = float(vix_quote.get("price", 15.50)) if vix_quote else 15.50
    regime = MarketRegimeDetector.detect_regime(candles_5m, india_vix=vix_val, symbol=sym)

    # Macro & Financial News Risk Engine
    news_events = NewsAndEventRiskEngine.get_market_news_and_events()

    decision = TradingDecisionEngine.evaluate(
        spot_price=spot,
        indicators=ind_sc,
        mtf_data=mtf_data,
        order_flow=order_flow,
        market_structure=structure,
        market_breadth=breadth,
        buy_priority_mode=True,
        smc_data=smc_analysis,
        symbol=sym,
        timeframe="5m",
        market_status=status_info,
        data_mode=status_info.get("data_mode", "HISTORICAL"),
        is_stale=status_info.get("is_stale", False),
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

    buyer_pct = order_flow.get("buyer_percentage")
    buyer_pct_float = float(buyer_pct) if buyer_pct is not None else 50.0
    flow_state = order_flow.get("order_flow_state", "NEUTRAL")
    if flow_state == "UNAVAILABLE":
        of_label = "Unavailable"
    elif buyer_pct_float >= 52.0 or "BUYING" in flow_state:
        of_label = "Buyers Dominating"
    elif buyer_pct_float <= 48.0 or "SELLING" in flow_state:
        of_label = "Sellers Dominating"
    else:
        of_label = "Balanced"

    # Check if active options intelligence already exists in cache (e.g. from live feed sync)
    existing_opt = cache.analytics.get(sym, {}).get("options_intelligence", {})
    if existing_opt and existing_opt.get("status") not in ("UNAVAILABLE", None) and existing_opt.get("pcr_oi") is not None:
        opt_analysis = existing_opt
    else:
        opt_analysis = OptionsAnalytics.get_options_intelligence(sym, spot, allow_sample=True)
    opt_sentiment = opt_analysis.get("sentiment", "Unavailable")
    perf_metrics = PerformanceAnalytics.get_performance_metrics(sym)

    # Authoritative CVD anchored to session
    is_cvd_avail = order_flow.get("is_cvd_available", False)
    shared_session_cvd = order_flow.get("session_cvd")

    call_wall = opt_analysis.get("major_resistance_strike") or opt_analysis.get("call_wall")
    put_wall = opt_analysis.get("major_support_strike") or opt_analysis.get("put_wall")

    market_intelligence = {
        "market_structure": ms_label,
        "vwap_position": vwap_pos,
        "vwap_value": round(vwap_val, 2),
        "order_flow": of_label,
        "buyer_percentage": round(buyer_pct_float, 1) if buyer_pct is not None else 50.0,
        "is_cvd_available": is_cvd_avail,
        "cvd": shared_session_cvd,
        "session_cvd": shared_session_cvd,
        "timeframe_cvd": order_flow.get("timeframe_cvd"),
        "candle_delta": order_flow.get("candle_delta"),
        "cvd_display": order_flow.get("cvd_display", "CVD UNAVAILABLE"),
        "options_sentiment": opt_sentiment,
        "options_details": opt_analysis.get("details", ""),
        "options_pcr": opt_analysis.get("pcr_oi"),
        "call_wall": call_wall,
        "put_wall": put_wall,
        "market_regime": regime.get("regime", "SIDEWAYS_CONSOLIDATION"),
        "regime_strategy": regime.get("actionable_strategy", "NEUTRAL"),
        "data_status": status_info,
    }

    # Attach market intelligence, regime, news risk, and 4-tier MTF to decision payload
    decision["market_intelligence"] = market_intelligence
    decision["market_regime"] = regime
    decision["news_and_events"] = news_events
    decision["multi_timeframe_4tf"] = inst_4tf

    if put_wall and not structure.get("nearest_support"):
        structure["nearest_support"] = put_wall
    if call_wall and not structure.get("nearest_resistance"):
        structure["nearest_resistance"] = call_wall

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
        "institutional_4tf": inst_4tf,
        "market_regime": regime,
        "news_and_events": news_events,
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
    last_options_refresh = 0.0

    while True:
        try:
            now_ts = time.time()
            # Periodic background options refresh every 30 seconds for active indices via Angel One SmartAPI
            if now_ts - last_options_refresh > 30.0:
                try:
                    from data.angel_provider import get_angel_provider
                    get_angel_provider().poll_options_data()
                    last_options_refresh = now_ts
                except Exception as oe:
                    logger.warning(f"Background options refresh error: {oe}")

            # 1. Update Quotes for Monitored Instruments FIRST so ticks are recorded
            quotes = {}
            for sym in MONITORED_INSTRUMENTS:
                q = client.get_quote(sym)
                quotes[sym] = q
                cache.update_quote(sym, q)

            # 2. Update Market Session Status (reflecting recent ticks)
            market_status = client.get_market_status()
            cache.update_market_status(market_status)

            # 3. Process NIFTY and BANKNIFTY
            for sym in ["NIFTY", "BANKNIFTY"]:
                process_symbol_pipeline(sym, quotes.get(sym))

            status_mgr = get_market_status_manager()
            market_data_status = {
                "NIFTY": status_mgr.get_status("NIFTY"),
                "BANKNIFTY": status_mgr.get_status("BANKNIFTY"),
                "INDIAVIX": status_mgr.get_status("INDIAVIX"),
            }

            any_live = any(s.get("status") == "LIVE" for s in market_data_status.values())
            api_state = "LIVE_STREAM" if any_live else ("LIVE_AUTHENTICATED" if client.is_authenticated else "OFFLINE_SIMULATION")
            cache.update_system_status(api_state, "Continuous market stream active.")
            cache.save_to_snapshot()

            # Broadcast live packet to all connected web clients
            packet = {
                "type": "TICK_UPDATE",
                "timestamp": get_ist_now().strftime("%Y-%m-%d %H:%M:%S IST"),
                "quotes": quotes,
                "market_status": market_status,
                "market_data_status": market_data_status,
                "active_symbol": "NIFTY",
                "analytics": cache.analytics.get("NIFTY", {}),
                "forecasts": cache.forecasts.get("NIFTY", {}),
                "signals": cache.signals.get("NIFTY", {}),
                "market_regime": cache.analytics.get("NIFTY", {}).get("market_regime", {}),
                "news_and_events": cache.analytics.get("NIFTY", {}).get("news_and_events", {}),
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

async def daily_session_refresh_scheduler_task():
    """
    Requirement 5:
    Daily background scheduler running every 30 seconds to check and refresh
    the Angel One SmartAPI session at 08:50 AM IST before market open.
    """
    logger.info("Daily 08:50 AM IST SmartAPI Session Refresh Scheduler started.")
    while True:
        try:
            from data.angel_provider import get_angel_provider
            get_angel_provider().check_and_refresh_session()
        except Exception as e:
            logger.debug(f"Session scheduler error: {e}")
        await asyncio.sleep(30.0)

async def continuous_options_polling_task():
    """
    Requirement 2:
    Rate-Safe 30-Second Polling Loop: Runs every 30 seconds respecting
    SmartAPI rate limits. Batches ATM CE/PE contracts for NIFTY and BANKNIFTY
    in a single call (up to 50 tokens) and computes live PCR and OI walls.
    """
    logger.info("Continuous 30s Options Polling Task started.")
    await asyncio.sleep(5.0)
    while True:
        try:
            from data.angel_provider import get_angel_provider
            angel_prov = get_angel_provider()
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, angel_prov.poll_options_data)
        except Exception as e:
            logger.warning(f"Error in continuous options polling: {e}")
        await asyncio.sleep(30.0)

@app.on_event("startup")
async def startup_event():
    """
    Server startup orchestration:
    1. Authenticate Angel One SmartAPI via TOTP.
    2. Fetch 5-day FIVE_MINUTE startup candles for NIFTY (99926000), BANKNIFTY (99926009), INDIA VIX (99926017).
    3. Dynamically resolve nearest monthly NIFTY NFO FUTIDX contract from OpenAPIScripMaster.json.
    4. Start SmartWebSocketV2 (mode 3) for live ticks & futures metrics (scaled / 100.0).
    6. Initial batched options poll (PCR & OI walls) for NIFTY & BANKNIFTY.
    7. Pre-calculate analytics, indicators (EMA 10/20, ADX), and forecasts so charts populate immediately.
    8. Start daily 08:50 AM IST session refresh scheduler, continuous monitor, and 30s options loop.
    """
    if os.getenv("TESTING", "0") == "1":
        return

    logger.info("Initializing Live Indian Market Terminal...")

    # 1. Authenticate Angel One SmartAPI and fetch startup candles (Requirement 1 & 2)
    try:
        from data.angel_provider import get_angel_provider
        angel_prov = get_angel_provider()
        if angel_prov.authenticate():
            # Startup 5m candles for NIFTY, BANKNIFTY, INDIAVIX
            startup_candles = angel_prov.fetch_startup_candles(days=5)
            for sym, df_candles in startup_candles.items():
                if df_candles is not None and not df_candles.empty:
                    tf_suite = HistoricalDataManager.build_timeframe_suite(df_candles)
                    tf_suite["5m"] = df_candles
                    cache.set_candles(sym, tf_suite)

            # Dynamically resolve nearest monthly NIFTY NFO FUTIDX contract
            fut_contract = angel_prov.resolve_nearest_nifty_future()
            if fut_contract:
                logger.info(
                    f"Resolved nearest NIFTY Future: {fut_contract.get('symbol')} "
                    f"(Token: {fut_contract.get('token')}, Expiry: {fut_contract.get('expiry')})"
                )

            # Start SmartWebSocketV2 in mode 3
            angel_prov.start_websocket_stream()

            # Initial options poll for NIFTY and BANKNIFTY ATM strikes
            try:
                angel_prov.poll_options_data(force=True)
            except Exception as ope:
                logger.warning(f"Initial options poll warning: {ope}")
        else:
            logger.warning("Angel One SmartAPI authentication returned False on startup.")
    except Exception as ae:
        logger.error(f"Error initializing Angel One SmartAPI on startup: {ae}")

    # 2. Pre-populate quotes and execute analytics pipeline for NIFTY, BANKNIFTY
    try:
        for sym in ["NIFTY", "BANKNIFTY"]:
            q = client.get_quote(sym)
            cache.update_quote(sym, q)
            process_symbol_pipeline(sym, q)
        cache.save_to_snapshot()
        logger.info("Initial instrument pipelines processed and cached.")
    except Exception as pe:
        logger.warning(f"Error executing startup pipelines: {pe}")

    # 4. Start background monitoring worker, 30s options task, and daily 08:50 AM IST refresh scheduler
    asyncio.create_task(continuous_market_monitor_task())
    asyncio.create_task(daily_session_refresh_scheduler_task())
    asyncio.create_task(continuous_options_polling_task())

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

@app.get("/api/version")
def get_version():
    """Version and runtime diagnostic endpoint for deployment verification."""
    now_ist = get_ist_now()
    status_mgr = get_market_status_manager()
    return {
        "status": "healthy",
        "app": "live-market-terminal",
        "version": "1.2.0-live-public-feed",
        "timestamp_ist": now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "is_authenticated": client.is_authenticated,
        "provider_name": client.provider_name,
        "market_data_status": {
            "NIFTY": status_mgr.get_status("NIFTY"),
            "BANKNIFTY": status_mgr.get_status("BANKNIFTY"),
        },
    }

@app.get("/api/overview")
def get_overview():
    """Returns quotes, exchange clock, market status, and authoritative feed status."""
    snap = cache.get_snapshot()
    status_mgr = get_market_status_manager()
    overview_data = {
        "quotes": snap.get("quotes", {}),
        "market_status": snap.get("market_status", {}),
        "market_data_status": {
            "NIFTY": status_mgr.get_status("NIFTY"),
            "BANKNIFTY": status_mgr.get_status("BANKNIFTY"),
            "INDIAVIX": status_mgr.get_status("INDIAVIX"),
        },
        "system_status": snap.get("system_status", {}),
    }
    return status_mgr.create_response_envelope(
        instrument="NIFTY",
        payload=overview_data
    )

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

    status_mgr = get_market_status_manager()
    return status_mgr.create_response_envelope(
        instrument=sym,
        payload={
            "symbol": sym,
            "timeframe": tf,
            "count": len(bars),
            "bars": bars,
        }
    )

@app.get("/api/internals")
def get_internals(symbol: str = "NIFTY"):
    """Returns order flow, CVD, market structure, breadth, and institutional flow."""
    sym = symbol.upper()
    if sym not in cache.analytics or not cache.analytics[sym] or "market_intelligence" not in cache.analytics[sym]:
        process_symbol_pipeline(sym)
    status_mgr = get_market_status_manager()
    analytics_data = cache.analytics.get(sym, {})
    return status_mgr.create_response_envelope(
        instrument=sym,
        payload=analytics_data
    )

@app.get("/api/decision")
def get_decision(symbol: str = "NIFTY"):
    """Returns BUY / SELL / WAIT trading decision and playbook."""
    sym = symbol.upper()
    if sym not in cache.signals or not cache.signals[sym] or "clean_recommendation" not in cache.signals[sym]:
        process_symbol_pipeline(sym)
    status_mgr = get_market_status_manager()
    sig = cache.signals.get(sym, {})
    return status_mgr.create_response_envelope(
        instrument=sym,
        payload=sig
    )

@app.get("/api/forecasts")
def get_forecasts(symbol: str = "NIFTY"):
    """Returns multi-horizon directional forecasts."""
    sym = symbol.upper()
    if sym not in cache.forecasts or not cache.forecasts[sym]:
        process_symbol_pipeline(sym)
    status_mgr = get_market_status_manager()
    fcasts = cache.forecasts.get(sym, {})
    return status_mgr.create_response_envelope(
        instrument=sym,
        payload=fcasts
    )

@app.get("/api/options")
def get_options(symbol: str = "NIFTY", refresh: bool = False):
    """Returns Put-Call Ratio, Open Interest shifts, Max Pain, and strike radar."""
    sym = symbol.upper()
    analytics_data = cache.analytics.get(sym, {})
    opt_data = analytics_data.get("options_intelligence")

    if refresh or not opt_data or opt_data.get("status") in ("UNAVAILABLE", None):
        process_symbol_pipeline(sym)
        analytics_data = cache.analytics.get(sym, {})
        opt_data = analytics_data.get("options_intelligence")

    if not opt_data or opt_data.get("status") in ("UNAVAILABLE", None):
        opt_data = OptionsAnalytics.get_options_intelligence(sym, allow_sample=True)

    status_mgr = get_market_status_manager()
    return status_mgr.create_response_envelope(
        instrument=sym,
        payload=opt_data
    )

@app.get("/api/performance")
def get_performance(symbol: str = "NIFTY"):
    """Returns historical accuracy, win rate, average R:R, max drawdown, and false signal rate."""
    sym = symbol.upper()
    if sym not in cache.analytics or not cache.analytics[sym] or "performance" not in cache.analytics[sym]:
        process_symbol_pipeline(sym)
    status_mgr = get_market_status_manager()
    analytics_data = cache.analytics.get(sym, {})
    perf_data = analytics_data.get("performance", PerformanceAnalytics.get_performance_metrics(sym))
    return status_mgr.create_response_envelope(
        instrument=sym,
        payload=perf_data
    )

@app.get("/api/smc")
def get_smc(symbol: str = "NIFTY"):
    """Returns Smart Money Concepts (BOS, CHoCH, Liquidity Sweeps, Order Blocks, FVGs)."""
    sym = symbol.upper()
    if sym not in cache.analytics or not cache.analytics[sym] or "smc" not in cache.analytics[sym]:
        process_symbol_pipeline(sym)
    status_mgr = get_market_status_manager()
    analytics_data = cache.analytics.get(sym, {})
    smc_data = analytics_data.get("smc", {})
    return status_mgr.create_response_envelope(
        instrument=sym,
        payload=smc_data
    )

@app.get("/api/orderflow")
def get_orderflow(symbol: str = "NIFTY"):
    """Returns order flow, CVD, Volume Profile (POC/VAH/VAL), and VWAP bands."""
    sym = symbol.upper()
    if sym not in cache.analytics or not cache.analytics[sym] or "order_flow" not in cache.analytics[sym]:
        process_symbol_pipeline(sym)
    status_mgr = get_market_status_manager()
    analytics_data = cache.analytics.get(sym, {})
    of_data = analytics_data.get("order_flow", {})
    return status_mgr.create_response_envelope(
        instrument=sym,
        payload=of_data
    )

@app.get("/api/regime")
def get_market_regime(symbol: str = "NIFTY"):
    """Returns detected market regime (Trending, Sideways, Volatile), ADX, Choppiness Index, and Bollinger Bandwidth."""
    sym = symbol.upper()
    if sym not in cache.analytics or not cache.analytics[sym] or "market_regime" not in cache.analytics[sym]:
        process_symbol_pipeline(sym)
    status_mgr = get_market_status_manager()
    analytics_data = cache.analytics.get(sym, {})
    regime_data = analytics_data.get("market_regime", {})
    return status_mgr.create_response_envelope(
        instrument=sym,
        payload=regime_data
    )

@app.get("/api/news")
def get_news_and_events():
    """Returns top financial headlines, sentiment score, and macroeconomic calendar risk events."""
    news_data = NewsAndEventRiskEngine.get_market_news_and_events()
    status_mgr = get_market_status_manager()
    return status_mgr.create_response_envelope(
        instrument="NIFTY",
        payload=news_data
    )

@app.get("/api/greeks")
def get_option_greeks(symbol: str = "NIFTY"):
    """Returns ATM option Greeks (Delta, Gamma, Theta, Vega), IV Skew, and verified strike radar."""
    sym = symbol.upper()
    analytics_data = cache.analytics.get(sym, {})
    opt_data = analytics_data.get("options_intelligence")
    if not opt_data or opt_data.get("status") in ("UNAVAILABLE", None):
        process_symbol_pipeline(sym)
        analytics_data = cache.analytics.get(sym, {})
        opt_data = analytics_data.get("options_intelligence")
    if not opt_data or opt_data.get("status") in ("UNAVAILABLE", None):
        opt_data = OptionsAnalytics.get_options_intelligence(sym, allow_sample=True)
    status_mgr = get_market_status_manager()
    greeks_data = {
        "symbol": sym,
        "underlying_price": opt_data.get("underlying_price"),
        "atm_strike": opt_data.get("atm_strike"),
        "atm_iv": opt_data.get("atm_iv"),
        "iv_skew": opt_data.get("iv_skew"),
        "atm_greeks": opt_data.get("atm_greeks", {}),
        "exchange_verification": opt_data.get("exchange_verification", {}),
        "sentiment": opt_data.get("sentiment"),
        "pcr_oi": opt_data.get("pcr_oi"),
        "max_pain": opt_data.get("max_pain"),
        "strike_radar": opt_data.get("strike_radar", []),
        "last_updated": opt_data.get("last_updated"),
    }
    return status_mgr.create_response_envelope(
        instrument=sym,
        payload=greeks_data
    )

@app.get("/api/mtf")
def get_multi_timeframe(symbol: str = "NIFTY"):
    """Returns 4-tier institutional confluence matrix across 5m, 15m, 1h, and daily timeframes."""
    sym = symbol.upper()
    if sym not in cache.analytics or not cache.analytics[sym] or "institutional_4tf" not in cache.analytics[sym]:
        process_symbol_pipeline(sym)
    status_mgr = get_market_status_manager()
    analytics_data = cache.analytics.get(sym, {})
    mtf_payload = {
        "symbol": sym,
        "institutional_4tf": analytics_data.get("institutional_4tf", {}),
        "mtf_summary": analytics_data.get("mtf", {}),
    }
    return status_mgr.create_response_envelope(
        instrument=sym,
        payload=mtf_payload
    )

@app.get("/api/health")
def get_health():
    """Returns API health, data freshness, and active connections."""
    snap = cache.get_snapshot()
    status_mgr = get_market_status_manager()
    health_data = {
        "status": "HEALTHY",
        "active_clients": len(manager.active_connections),
        "system_status": snap.get("system_status", {}),
        "market_data_status": {
            "NIFTY": status_mgr.get_status("NIFTY"),
            "BANKNIFTY": status_mgr.get_status("BANKNIFTY"),
            "INDIAVIX": status_mgr.get_status("INDIAVIX"),
        },
    }
    return status_mgr.create_response_envelope(
        instrument="NIFTY",
        payload=health_data
    )

@app.post("/api/feed/sync")
async def sync_external_feed(packet: Dict[str, Any]):
    """
    Ingests live market feed snapshot or tick data from local trading terminal or data pump.
    Updates in-memory market cache and immediately broadcasts live packet to all connected browser clients.
    """
    try:
        quotes = packet.get("quotes")
        status_mgr = get_market_status_manager()

        if quotes and isinstance(quotes, dict):
            for sym, q in quotes.items():
                if isinstance(q, dict):
                    cache.update_quote(sym, q)
                    if q.get("is_live"):
                        status_mgr.record_tick(sym)
                        status_mgr.set_provider_status(True, q.get("source", "Live Bridge Feed"))

        options_chain = packet.get("options_chain") or packet.get("option_chains")
        if options_chain and isinstance(options_chain, dict):
            try:
                from data.options_feed import NSEOptionChainFeed
                for oc_sym, oc_data in options_chain.items():
                    if isinstance(oc_data, dict) and oc_data.get("records"):
                        sym_u = oc_sym.upper()
                        NSEOptionChainFeed._mem_cache[sym_u] = oc_data
                        NSEOptionChainFeed._cache_timestamps[sym_u] = time.time()
                        NSEOptionChainFeed._save_to_disk_cache(sym_u, oc_data)
            except Exception as oce:
                logger.warning(f"Error caching synced option chain: {oce}")

        analytics = packet.get("analytics")
        if analytics and isinstance(analytics, dict):
            for sym, data in analytics.items():
                sym_u = sym.upper()
                if sym_u in cache.analytics and isinstance(cache.analytics[sym_u], dict) and isinstance(data, dict):
                    cache.analytics[sym_u].update(data)
                else:
                    cache.update_analytics(sym_u, data)

        signals = packet.get("signals")
        if signals and isinstance(signals, dict):
            for sym, sig in signals.items():
                cache.update_signals(sym, sig)

        forecasts = packet.get("forecasts")
        if forecasts and isinstance(forecasts, dict):
            for sym, fcasts in forecasts.items():
                cache.update_forecasts(sym, fcasts)

        market_status = packet.get("market_status")
        if market_status and isinstance(market_status, dict):
            cache.update_market_status(market_status)

        cache.update_system_status("LIVE_STREAM", "Continuous live feed synced from authenticated bridge.")

        # Broadcast packet to all connected WebSockets
        broadcast_packet = {
            "type": "TICK_UPDATE",
            "timestamp": get_ist_now().strftime("%Y-%m-%d %H:%M:%S IST"),
            "quotes": cache.quotes,
            "market_status": cache.market_status,
            "active_symbol": packet.get("active_symbol", "NIFTY"),
            "analytics": cache.analytics.get("NIFTY", {}),
            "forecasts": cache.forecasts.get("NIFTY", {}),
            "signals": cache.signals.get("NIFTY", {}),
            "market_regime": cache.analytics.get("NIFTY", {}).get("market_regime", {}),
            "news_and_events": cache.analytics.get("NIFTY", {}).get("news_and_events", {}),
            "analytics_by_symbol": cache.analytics,
            "forecasts_by_symbol": cache.forecasts,
            "signals_by_symbol": cache.signals,
            "system_status": cache.system_status,
        }
        await manager.broadcast(broadcast_packet)

        return {"status": "success", "message": "Feed synchronized and broadcast to all connected clients."}
    except Exception as e:
        logger.error(f"Error in sync_external_feed: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

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
            "INDIAVIX": status_mgr.get_status("INDIAVIX"),
        }
        init_packet = {
            "type": "INITIAL_STATE",
            "timestamp": get_ist_now().strftime("%Y-%m-%d %H:%M:%S IST"),
            "quotes": snap.get("quotes", {}),
            "market_status": snap.get("market_status", {}),
            "market_data_status": market_data_status,
            "active_symbol": "NIFTY",
            "analytics": cache.analytics.get("NIFTY", {}),
            "forecasts": cache.forecasts.get("NIFTY", {}),
            "signals": cache.signals.get("NIFTY", {}),
            "market_regime": cache.analytics.get("NIFTY", {}).get("market_regime", {}),
            "news_and_events": cache.analytics.get("NIFTY", {}).get("news_and_events", {}),
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
