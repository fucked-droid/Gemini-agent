"""
Reusable Streamlit UI Component Blocks.
Renders cards, metrics, and multi-timeframe matrices in dark institutional styling.
"""

import streamlit as st
from typing import Dict, Any

def render_overview_cards(quotes: Dict[str, Any], market_status: Dict[str, Any]):
    """Renders Section A: Live Market Overview metric cards."""
    col1, col2, col3, col4 = st.columns(4)

    # NIFTY
    q_nifty = quotes.get("NIFTY", {})
    p_nifty = q_nifty.get("price", 0.0)
    chg_nifty = q_nifty.get("change", 0.0)
    pct_nifty = q_nifty.get("change_pct", 0.0)
    col1.metric("NIFTY 50", f"₹{p_nifty:,.2f}", f"{chg_nifty:+.2f} ({pct_nifty:+.2f}%)")

    # BANKNIFTY
    q_bn = quotes.get("BANKNIFTY", {})
    p_bn = q_bn.get("price", 0.0)
    chg_bn = q_bn.get("change", 0.0)
    pct_bn = q_bn.get("change_pct", 0.0)
    col2.metric("BANKNIFTY", f"₹{p_bn:,.2f}", f"{chg_bn:+.2f} ({pct_bn:+.2f}%)")

    # INDIA VIX
    q_vix = quotes.get("INDIAVIX", {})
    p_vix = q_vix.get("price", 0.0)
    chg_vix = q_vix.get("change", 0.0)
    pct_vix = q_vix.get("change_pct", 0.0)
    col3.metric("INDIA VIX", f"{p_vix:.2f}", f"{chg_vix:+.2f} ({pct_vix:+.2f}%)")

    # Market Session Status
    phase = market_status.get("phase", "UNKNOWN")
    is_open = market_status.get("is_open", False)
    status_icon = "🟢" if is_open else "🟡"
    col4.metric("Market Status", f"{status_icon} {phase}", market_status.get("status", "CLOSED"))

def render_condition_banner(mtf_data: Dict[str, Any], breadth: Dict[str, Any], inst: Dict[str, Any]):
    """Renders Section B: Current Market Condition Banner."""
    trend = mtf_data.get("composite_trend", "SIDEWAYS")
    adv = breadth.get("advances", 25)
    dec = breadth.get("declines", 25)
    adr = breadth.get("adr", 1.0)
    inst_desc = inst.get("interpretation", "Unavailable")

    if "BULLISH" in trend:
        banner_color = "#1b4d3e"
        badge_color = "#26a69a"
    elif "BEARISH" in trend:
        banner_color = "#4d1b1b"
        badge_color = "#ef5350"
    else:
        banner_color = "#3d391b"
        badge_color = "#ffd600"

    st.markdown(
        f"""
        <div style="background-color: {banner_color}; border-left: 6px solid {badge_color}; padding: 12px 18px; border-radius: 6px; margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 1.15rem; font-weight: 700; color: #ffffff;">Current Regime: <span style="color: {badge_color};">{trend}</span></span>
                <span style="font-size: 0.95rem; color: #e6edf3;">Breadth: <b>{adv} Advances / {dec} Declines</b> (ADR: {adr:.2f})</span>
                <span style="font-size: 0.85rem; color: #8b949e;">Institutions: {inst_desc[:38]}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_mtf_matrix(mtf_data: Dict[str, Any]):
    """Renders Section E: Multi-Timeframe Analysis Matrix."""
    timeframes = mtf_data.get("timeframes", {})
    cols = st.columns(len(timeframes) if timeframes else 1)

    for idx, (tf, data) in enumerate(timeframes.items()):
        direction = data.get("direction", "SIDEWAYS")
        momentum = data.get("momentum", "NEUTRAL")
        conf = data.get("confidence_pct", 50.0)
        vwap_pos = data.get("vwap_position", "AT_VWAP")

        if direction == "BULLISH":
            border = "#26a69a"
            tag_bg = "rgba(38, 166, 154, 0.2)"
        elif direction == "BEARISH":
            border = "#ef5350"
            tag_bg = "rgba(239, 83, 80, 0.2)"
        else:
            border = "#ffd600"
            tag_bg = "rgba(255, 214, 0, 0.2)"

        with cols[idx]:
            st.markdown(
                f"""
                <div style="border: 1px solid {border}; border-radius: 6px; padding: 10px; background-color: #161b22; text-align: center;">
                    <div style="font-weight: 700; font-size: 1.05rem; color: #ffffff;">{tf}</div>
                    <div style="background-color: {tag_bg}; color: {border}; font-weight: 600; padding: 3px 6px; border-radius: 4px; margin: 6px 0; font-size: 0.85rem;">
                        {direction} ({conf:.0f}%)
                    </div>
                    <div style="font-size: 0.75rem; color: #8b949e;">{momentum}</div>
                    <div style="font-size: 0.75rem; color: #8b949e; margin-top: 3px;">{vwap_pos}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

def render_forecast_cards(forecast_suite: Dict[str, Any]):
    """Renders Section F: Movement Direction Forecasts."""
    horizons = forecast_suite.get("horizons", {})
    cols = st.columns(len(horizons) if horizons else 1)

    for idx, (h, data) in enumerate(horizons.items()):
        f_dir = data.get("direction", "FLAT")
        low = data.get("target_lower", 0.0)
        high = data.get("target_upper", 0.0)
        p_up = data.get("probability_up", 0.5)
        conf = data.get("confidence_pct", 50.0)

        color = "#26a69a" if f_dir == "UP" else ("#ef5350" if f_dir == "DOWN" else "#ffd600")

        with cols[idx]:
            st.markdown(
                f"""
                <div style="border-top: 3px solid {color}; background-color: #161b22; border-radius: 6px; padding: 10px; text-align: center;">
                    <div style="color: #8b949e; font-size: 0.85rem; font-weight: 600;">{h} Horizon</div>
                    <div style="color: {color}; font-size: 1.25rem; font-weight: 700; margin: 4px 0;">{f_dir}</div>
                    <div style="font-size: 0.8rem; color: #e6edf3;">₹{low:,.1f} - ₹{high:,.1f}</div>
                    <div style="font-size: 0.75rem; color: #8b949e; margin-top: 4px;">P(UP): {p_up * 100:.1f}% | Conf: {conf:.0f}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

def render_decision_card(decision: Dict[str, Any]):
    """Renders Section G: Trader's Action Playbook Card."""
    dec = decision.get("decision", "WAIT")
    conf = decision.get("confidence_pct", 50.0)
    entry = decision.get("entry_zone", "N/A")
    sl = decision.get("stop_loss", 0.0)
    t1 = decision.get("target_1", 0.0)
    t2 = decision.get("target_2", 0.0)
    rr = decision.get("risk_reward_ratio", "1:1.5")
    reasons = decision.get("reasons", [])
    invals = decision.get("invalidation_conditions", [])

    if dec == "BUY":
        border = "#26a69a"
        bg = "#11221c"
        badge_text = "BUY / LONG SETUP"
    elif dec == "SELL":
        border = "#ef5350"
        bg = "#261515"
        badge_text = "SELL / SHORT SETUP"
    else:
        border = "#ffd600"
        bg = "#232014"
        badge_text = "WAIT / NO TRADE (CHOP)"

    c1, c2 = st.columns([1, 2])

    with c1:
        st.markdown(
            f"""
            <div style="border: 2px solid {border}; background-color: {bg}; border-radius: 8px; padding: 18px; text-align: center;">
                <div style="background-color: {border}; color: #ffffff; font-weight: 800; font-size: 1.15rem; padding: 6px; border-radius: 4px; margin-bottom: 12px;">
                    {badge_text}
                </div>
                <div style="font-size: 0.9rem; color: #8b949e;">Signal Confidence</div>
                <div style="font-size: 1.8rem; font-weight: 700; color: #ffffff;">{conf:.0f}%</div>
                <hr style="border-color: #30363d; margin: 12px 0;">
                <div style="text-align: left; font-size: 0.85rem; line-height: 1.8;">
                    <div><b>Entry Zone:</b> {entry}</div>
                    <div><b>Stop Loss:</b> <span style="color: #ef5350;">₹{sl:,.2f}</span></div>
                    <div><b>Target 1:</b> <span style="color: #26a69a;">₹{t1:,.2f}</span></div>
                    <div><b>Target 2:</b> <span style="color: #26a69a;">₹{t2:,.2f}</span></div>
                    <div><b>Risk/Reward:</b> {rr}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown("#### 🎯 Execution Thesis & Rationale")
        for r in reasons[:4]:
            st.markdown(f"- {r}")

        st.markdown("#### ⚠️ Trade Invalidation Triggers")
        for inv in invals[:3]:
            st.markdown(f"- 🛑 {inv}")

        st.caption("Mandate: Analytical signal only. Zero automated trade placement.")

def render_system_status(sys_status: Dict[str, Any], market_status: Dict[str, Any]):
    """Renders Section H: System Status and Health."""
    col1, col2, col3, col4 = st.columns(4)

    api_st = sys_status.get("api_status", "UNKNOWN")
    col1.metric("API Provider", "DhanHQ REST & WSS", api_st)
    col2.metric("Data Freshness", f"{sys_status.get('data_freshness_seconds', 0.0)}s ago", "Fresh (< 60s)")
    col3.metric("Exchange Clock", market_status.get("timestamp", "N/A"), market_status.get("phase", "CLOSED"))
    col4.metric("Engine Refresh", f"Every {sys_status.get('refresh_interval', 30)}s", "Synchronized")
