"""
Interactive Plotly Charts for Live Market Terminal.
Includes multi-pane candlestick chart with EMA 10/20, VWAP, Volume delta,
CVD trend line, and Buyer/Seller pressure gauges.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, Any, Optional

def apply_dark_theme(fig: go.Figure, margin: Optional[Dict[str, int]] = None) -> go.Figure:
    """Applies standardized dark theme to Plotly figures without keyword collisions."""
    fig.update_layout(
        paper_bgcolor="#0e1117",
        plot_bgcolor="#161b22",
        font={"color": "#e6edf3", "family": "Inter, Roboto, sans-serif"},
        margin=margin or {"l": 50, "r": 50, "t": 40, "b": 30},
    )
    fig.update_xaxes(gridcolor="#30363d", showgrid=True)
    fig.update_yaxes(gridcolor="#30363d", showgrid=True)
    return fig

def create_candlestick_chart(
    df: pd.DataFrame,
    indicators: Dict[str, Any],
    symbol: str = "NIFTY",
    decision: Optional[Dict[str, Any]] = None,
) -> go.Figure:
    """
    Creates institutional multi-pane candlestick chart with:
    Pane 1: Candlesticks, EMA 10, EMA 20, VWAP, Buy/Sell Levels
    Pane 2: Volume Bars colored by delta
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No Candle Data Available", showarrow=False, font={"size": 18, "color": "#8b949e"})
        return apply_dark_theme(fig)

    # Create subplots with shared x-axis
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.75, 0.25],
        subplot_titles=(f"{symbol} Live Price Action & Structure", "Volume & Delta"),
    )

    # 1. Candlestick trace
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
            increasing_fillcolor="#26a69a",
            decreasing_fillcolor="#ef5350",
        ),
        row=1,
        col=1,
    )

    # 2. Moving Averages & VWAP
    if "EMA10" in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df["EMA10"], mode="lines", name="EMA 10", line=dict(color="#00e5ff", width=1.5)),
            row=1,
            col=1,
        )

    if "EMA20" in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df["EMA20"], mode="lines", name="EMA 20", line=dict(color="#ff4081", width=1.5)),
            row=1,
            col=1,
        )

    if "VWAP" in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df["VWAP"], mode="lines", name="VWAP", line=dict(color="#ffd600", width=2.0, dash="dot")),
            row=1,
            col=1,
        )

    # 3. Decision Target / SL Overlay lines
    if decision and decision.get("decision") in ("BUY", "SELL"):
        sl = decision.get("stop_loss")
        t1 = decision.get("target_1")
        if sl:
            fig.add_hline(y=sl, line_dash="dash", line_color="#ef5350", annotation_text=f"SL: ₹{sl:,.1f}", row=1, col=1)
        if t1:
            fig.add_hline(y=t1, line_dash="dash", line_color="#26a69a", annotation_text=f"Target: ₹{t1:,.1f}", row=1, col=1)

    # 4. Volume Bar Pane
    colors = ["#26a69a" if c >= o else "#ef5350" for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(
        go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color=colors, opacity=0.8),
        row=2,
        col=1,
    )

    # Formatting
    fig.update_layout(
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=520,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(title_text="Price (₹)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return apply_dark_theme(fig, margin={"l": 50, "r": 50, "t": 40, "b": 30})

def create_cvd_chart(df_flow: pd.DataFrame) -> go.Figure:
    """
    Creates Cumulative Volume Delta (CVD) line chart with fill.
    """
    if df_flow.empty or "CVD" not in df_flow.columns:
        fig = go.Figure()
        fig.add_annotation(text="No CVD Data", showarrow=False, font={"size": 16, "color": "#8b949e"})
        return apply_dark_theme(fig)

    last_cvd = df_flow["CVD"].iloc[-1]
    line_color = "#26a69a" if last_cvd >= 0 else "#ef5350"

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_flow.index,
            y=df_flow["CVD"],
            mode="lines",
            name="Session CVD",
            line=dict(color=line_color, width=2.5),
            fill="tozeroy",
            fillcolor="rgba(38, 166, 154, 0.15)" if last_cvd >= 0 else "rgba(239, 83, 80, 0.15)",
        )
    )

    fig.add_hline(y=0, line_dash="dot", line_color="#8b949e")

    fig.update_layout(
        template="plotly_dark",
        title="Cumulative Volume Delta (CVD)",
        height=260,
    )
    return apply_dark_theme(fig, margin={"l": 40, "r": 30, "t": 35, "b": 25})

def create_pressure_gauge(buyer_pct: float) -> go.Figure:
    """
    Renders Donut / Gauge indicating Buyer vs Seller Volume Pressure.
    """
    seller_pct = 100.0 - buyer_pct
    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Buyers", "Sellers"],
                values=[buyer_pct, seller_pct],
                hole=0.65,
                marker=dict(colors=["#26a69a", "#ef5350"]),
                textinfo="percent+label",
                hoverinfo="label+value",
            )
        ]
    )
    fig.update_layout(
        template="plotly_dark",
        title="Buying vs Selling Pressure",
        showlegend=False,
        height=260,
        annotations=[
            dict(
                text=f"<b>{buyer_pct:.1f}%</b><br>Buyers",
                x=0.5,
                y=0.5,
                font_size=14,
                font_color="#26a69a" if buyer_pct >= 50 else "#ef5350",
                showarrow=False,
            )
        ],
    )
    return apply_dark_theme(fig, margin={"l": 20, "r": 20, "t": 40, "b": 20})
