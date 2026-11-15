"""
Live Indian Market Terminal — Professional Institutional Browser Dashboard.
Built with Streamlit & Plotly. Synchronized with central MarketCache and CLI terminal.
"""

import os
import sys
import time
import datetime
from pathlib import Path

# Add live-market-terminal to sys.path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import streamlit as st
import pandas as pd

from config import DEFAULT_REFRESH_INTERVAL_SECONDS, MONITORED_INSTRUMENTS, TOP_NIFTY_CONSTITUENTS
from data import DhanClient, HistoricalDataManager, get_global_cache
from analytics import (
    TechnicalIndicators,
    OrderFlowAnalyzer,
    MarketStructureAnalyzer,
    MarketBreadthAnalyzer,
    MultiTimeframeEngine,
)
from prediction import ForecastOrchestrator
from signals import TradingDecisionEngine
from dashboard.layout import apply_institutional_theme
from dashboard.components import (
    render_overview_cards,
    render_condition_banner,
    render_mtf_matrix,
    render_forecast_cards,
    render_decision_card,
    render_system_status,
)
from dashboard.charts import (
    create_candlestick_chart,
    create_cvd_chart,
    create_pressure_gauge,
)

# Apply global styling
apply_institutional_theme()

# Initialize cache and client in session state
if "cache" not in st.session_state:
    st.session_state.cache = get_global_cache()

if "client" not in st.session_state:
    st.session_state.client = DhanClient()

if "last_refresh_time" not in st.session_state:
    st.session_state.last_refresh_time = 0.0

cache = st.session_state.cache
client = st.session_state.client

# ==========================================
# SIDEBAR CONTROLS
# ==========================================
st.sidebar.title("⚡ Control Panel")

selected_symbol = st.sidebar.selectbox("Active Instrument", ["NIFTY", "BANKNIFTY"], index=0)
selected_timeframe = st.sidebar.selectbox("Chart Timeframe", ["5m", "1m", "15m", "30m", "60m"], index=0)

auto_refresh = st.sidebar.checkbox("Auto Refresh (30s)", value=True)
manual_refresh = st.sidebar.button("🔄 Refresh Now", use_container_width=True)

st.sidebar.divider()
st.sidebar.subheader("API Integration")
cred_state = "Connected (DhanHQ LIVE)" if client.is_authenticated else "Offline Mode (Historical / Simulation)"
cred_color = "🟢" if client.is_authenticated else "🟡"
st.sidebar.markdown(f"**Status:** {cred_color} {cred_state}")
st.sidebar.caption("Credentials loaded from environment variables (.env). Zero token exposure.")

# ==========================================
# REFRESH LOGIC & PIPELINE
# ==========================================
now = time.time()
needs_refresh = (
    manual_refresh
    or (now - st.session_state.last_refresh_time >= DEFAULT_REFRESH_INTERVAL_SECONDS and auto_refresh)
    or (st.session_state.last_refresh_time == 0.0)
)

if needs_refresh:
    # 1. Update Market Session Status
    market_status = client.get_market_status()
    cache.update_market_status(market_status)

    # 2. Update Quotes
    for sym in MONITORED_INSTRUMENTS:
        q = client.get_quote(sym)
        cache.update_quote(sym, q)

    # 3. Candles and Analytics for Selected Symbol
    candles_1m = client.get_historical_candles(selected_symbol, interval="1m", days=3)
    tf_suite = HistoricalDataManager.build_timeframe_suite(candles_1m)
    cache.set_candles(selected_symbol, tf_suite)

    # Primary analysis candle
    chart_candles = tf_suite.get(selected_timeframe, candles_1m)
    df_enriched, indicators_sc = TechnicalIndicators.calculate_all(chart_candles)

    # Order Flow, Structure, Breadth
    order_flow_data = OrderFlowAnalyzer.analyze_order_flow(chart_candles)
    market_structure_data = MarketStructureAnalyzer.analyze_structure(chart_candles)
    breadth_data = MarketBreadthAnalyzer.compute_breadth_from_constituents(TOP_NIFTY_CONSTITUENTS)
    inst_flow = MarketBreadthAnalyzer.get_institutional_flow()

    # MTF Alignment
    mtf_data = MultiTimeframeEngine.evaluate_multi_timeframe_suite(tf_suite)

    # Forecasts
    spot_price = cache.quotes.get(selected_symbol, {}).get("price", 25144.30)
    atr = indicators_sc.get("atr", spot_price * 0.005)
    forecast_suite = ForecastOrchestrator.run_prediction_pipeline(df_enriched, spot_price, atr)

    # Trading Decision
    decision_data = TradingDecisionEngine.evaluate(
        spot_price=spot_price,
        indicators=indicators_sc,
        mtf_data=mtf_data,
        order_flow=order_flow_data,
        market_structure=market_structure_data,
        market_breadth=breadth_data,
    )

    # Update cache
    cache.update_analytics(selected_symbol, {
        "indicators": indicators_sc,
        "order_flow": order_flow_data,
        "market_structure": market_structure_data,
        "market_breadth": breadth_data,
        "institutional_flow": inst_flow,
        "mtf": mtf_data,
        "df_enriched": df_enriched,
    })
    cache.update_forecasts(selected_symbol, forecast_suite)
    cache.update_signals(selected_symbol, decision_data)

    api_state = "LIVE_AUTHENTICATED" if client.is_authenticated else "OFFLINE_SIMULATION"
    cache.update_system_status(api_state, "Synchronized")
    cache.save_to_snapshot()

    st.session_state.last_refresh_time = now

# Retrieve snapshot for rendering
snapshot = cache.get_snapshot()
quotes = snapshot.get("quotes", {})
market_status = snapshot.get("market_status", {})
analytics = snapshot.get("analytics", {}).get(selected_symbol, {})
signals = snapshot.get("signals", {}).get(selected_symbol, {})
forecasts = snapshot.get("forecasts", {}).get(selected_symbol, {})
sys_status = snapshot.get("system_status", {})

# ==========================================
# MAIN DASHBOARD INTERFACE
# ==========================================
st.title("📈 Institutional Live Indian Market Terminal")

# SECTION A: LIVE MARKET OVERVIEW
st.subheader("A. Live Market Overview")
render_overview_cards(quotes, market_status)

# SECTION B: CURRENT MARKET CONDITION
st.subheader("B. Current Market Condition")
mtf_data = analytics.get("mtf", {})
breadth_data = analytics.get("market_breadth", {})
inst_flow = analytics.get("institutional_flow", {})
render_condition_banner(mtf_data, breadth_data, inst_flow)

# SECTION C: LIVE PRICE ACTION (CANDLESTICK + INDICATORS)
st.subheader(f"C. Live Price Action — {selected_symbol} ({selected_timeframe})")
df_enriched = analytics.get("df_enriched", pd.DataFrame())
indicators_sc = analytics.get("indicators", {})
candlestick_fig = create_candlestick_chart(df_enriched, indicators_sc, selected_symbol, signals)
st.plotly_chart(candlestick_fig, use_container_width=True)

# SECTION D: MARKET ANALYSIS (ORDER FLOW & STRUCTURE)
st.subheader("D. Market Analysis & Order Flow Internals")
col_d1, col_d2 = st.columns([2, 1])

with col_d1:
    order_flow = analytics.get("order_flow", {})
    df_cvd = order_flow.get("df_with_cvd", pd.DataFrame())
    cvd_fig = create_cvd_chart(df_cvd)
    st.plotly_chart(cvd_fig, use_container_width=True)

with col_d2:
    buyer_pct = order_flow.get("buyer_percentage", 50.0)
    gauge_fig = create_pressure_gauge(buyer_pct)
    st.plotly_chart(gauge_fig, use_container_width=True)

# Support & Resistance / Structure Details
struct_data = analytics.get("market_structure", {})
st.markdown(
    f"**Structure Status:** `{struct_data.get('structure_state', 'CONSOLIDATION')}` | "
    f"**Event:** `{struct_data.get('event', 'NONE')}` | "
    f"**Nearest Support:** `₹{struct_data.get('nearest_support', 0.0):,.1f}` | "
    f"**Nearest Resistance:** `₹{struct_data.get('nearest_resistance', 0.0):,.1f}`"
)

# SECTION E: MULTI-TIMEFRAME ANALYSIS
st.subheader("E. Multi-Timeframe Alignment (1m to 60m)")
render_mtf_matrix(mtf_data)

# SECTION F: NEXT MARKET DIRECTION (FORECASTS)
st.subheader("F. Next Market Direction Forecasts")
render_forecast_cards(forecasts)

# SECTION G: TRADER'S DECISION ENGINE
st.subheader("G. Trader's Action Playbook (Rules-Based Engine)")
render_decision_card(signals)

# SECTION H: SYSTEM & FEED STATUS
st.subheader("H. System Status & Integrity")
render_system_status(sys_status, market_status)

# Auto-refresh loop via st.empty or sleep rerun if auto_refresh is enabled
if auto_refresh:
    time.sleep(1)
    # Check if countdown reached
    if time.time() - st.session_state.last_refresh_time >= DEFAULT_REFRESH_INTERVAL_SECONDS:
        st.rerun()
