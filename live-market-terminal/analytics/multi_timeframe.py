"""
Multi-Timeframe Market Analysis Engine.
Analyzes 5m, 15m, 1h, and Daily candles for:
- Trend direction (Bullish, Bearish, Sideways)
- Momentum (RSI + MACD Histogram)
- EMA alignment (EMA 10 vs EMA 20, EMA 20 vs EMA 50)
- VWAP positioning (Above/Below)
- Volume confirmation
- 4-Tier Institutional Confluence Alignment (5m, 15m, 1H, Daily)
- Explicitly quantified signal confidence (0-100%)
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from .indicators import TechnicalIndicators

logger = logging.getLogger("MultiTimeframeEngine")


class MultiTimeframeEngine:
    """
    Evaluates individual timeframes and synthesizes multi-timeframe alignment
    across tactical, intraday, session, and macro daily layers.
    """

    @classmethod
    def analyze_single_timeframe(cls, df: pd.DataFrame, timeframe_label: str) -> Dict[str, Any]:
        """
        Analyzes a single timeframe's indicators and scores its directional state.
        """
        if df is None or df.empty or len(df) < 5:
            return {
                "timeframe": timeframe_label,
                "direction": "SIDEWAYS",
                "momentum": "NEUTRAL",
                "ema_alignment": "NEUTRAL",
                "vwap_position": "AT_VWAP",
                "volume_confirmed": False,
                "confidence_pct": 50.0,
                "bias_score": 0.0,
                "close": 0.0,
                "vwap": 0.0,
                "ema10": 0.0,
                "ema20": 0.0,
                "rsi": 50.0,
            }

        df_ind, sc = TechnicalIndicators.calculate_all(df)
        close = sc["close"]
        ema10 = sc["ema10"]
        ema20 = sc["ema20"]
        vwap = sc["vwap"]
        rsi = sc["rsi"]
        macd_hist = sc["macd_hist"]

        # EMA Alignment
        if ema10 > ema20 * 1.0005:
            ema_align = "BULLISH_STACK"
            ema_score = 1.0
        elif ema10 < ema20 * 0.9995:
            ema_align = "BEARISH_STACK"
            ema_score = -1.0
        else:
            ema_align = "COMPRESSED"
            ema_score = 0.0

        # VWAP Position (for daily bars, compares against SMA20 if VWAP is equal to close)
        if close > vwap * 1.0005:
            vwap_pos = "ABOVE_VWAP"
            vwap_score = 1.0
        elif close < vwap * 0.9995:
            vwap_pos = "BELOW_VWAP"
            vwap_score = -1.0
        else:
            vwap_pos = "AT_VWAP"
            vwap_score = 0.0

        # Momentum
        if rsi > 54 and macd_hist > 0:
            momentum = "BULLISH_EXPANSION"
            mom_score = 1.0
        elif rsi < 46 and macd_hist < 0:
            momentum = "BEARISH_EXPANSION"
            mom_score = -1.0
        elif rsi >= 70:
            momentum = "OVERBOUGHT_EXTREME"
            mom_score = 0.5
        elif rsi <= 30:
            momentum = "OVERSOLD_EXTREME"
            mom_score = -0.5
        else:
            momentum = "NEUTRAL"
            mom_score = 0.0

        # Volume Confirmation
        vol = df["Volume"].iloc[-1] if "Volume" in df.columns else 0
        avg_vol = df["Volume"].tail(10).mean() if "Volume" in df.columns else 0
        vol_confirmed = bool(vol >= avg_vol * 0.9) if avg_vol > 0 else True
        vol_score = 0.5 if vol_confirmed else 0.0

        # Composite Timeframe Bias (-3.0 to +3.0)
        raw_score = ema_score + vwap_score + mom_score
        if raw_score >= 1.5:
            direction = "BULLISH"
        elif raw_score <= -1.5:
            direction = "BEARISH"
        else:
            direction = "SIDEWAYS"

        confidence = 50.0 + (abs(raw_score) / 3.0) * 35.0 + (10.0 if vol_confirmed else 0.0)
        confidence = min(round(confidence, 1), 95.0)

        return {
            "timeframe": timeframe_label,
            "direction": direction,
            "momentum": momentum,
            "ema_alignment": ema_align,
            "vwap_position": vwap_pos,
            "volume_confirmed": vol_confirmed,
            "confidence_pct": confidence,
            "bias_score": round(raw_score, 2),
            "close": close,
            "vwap": vwap,
            "ema10": ema10,
            "ema20": ema20,
            "rsi": rsi,
        }

    @classmethod
    def evaluate_multi_timeframe_suite(
        cls,
        timeframe_suite: Dict[str, pd.DataFrame],
        daily_df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """
        Runs comprehensive multi-timeframe analysis across intraday (1m, 5m, 15m, 30m, 60m)
        and institutional 4-tier confluence (5m, 15m, 1H, Daily).
        """
        results = {}
        standard_tfs = ["1m", "5m", "15m", "30m", "60m"]
        bullish_count = 0
        bearish_count = 0

        for tf in standard_tfs:
            df = timeframe_suite.get(tf, pd.DataFrame())
            res = cls.analyze_single_timeframe(df, tf)
            results[tf] = res
            if res["direction"] == "BULLISH":
                bullish_count += 1
            elif res["direction"] == "BEARISH":
                bearish_count += 1

        # Evaluate Daily Macro Timeframe
        df_daily = daily_df if daily_df is not None and not daily_df.empty else timeframe_suite.get("daily", pd.DataFrame())
        if df_daily.empty:
            df_daily = timeframe_suite.get("1d", pd.DataFrame())

        daily_res = cls.analyze_single_timeframe(df_daily, "daily")
        results["daily"] = daily_res

        # -------------------------------------------------------------
        # Institutional 4-Tier Confluence (5m, 15m, 1H, Daily)
        # -------------------------------------------------------------
        t_5m = results.get("5m", {})
        t_15m = results.get("15m", {})
        t_1h = results.get("60m", results.get("1h", {}))
        t_daily = results.get("daily", {})

        def score_dir(d: str) -> float:
            if d == "BULLISH":
                return 1.0
            elif d == "BEARISH":
                return -1.0
            return 0.0

        s_5m = score_dir(t_5m.get("direction", "SIDEWAYS"))
        s_15m = score_dir(t_15m.get("direction", "SIDEWAYS"))
        s_1h = score_dir(t_1h.get("direction", "SIDEWAYS"))
        s_daily = score_dir(t_daily.get("direction", "SIDEWAYS"))

        total_confluence_score = (s_5m * 0.4) + (s_15m * 0.6) + (s_1h * 0.8) + (s_daily * 1.0)
        norm_score = round(max(-2.0, min(2.0, (total_confluence_score / 2.8) * 2.0)), 2)

        bull_4tf = sum(1 for s in [s_5m, s_15m, s_1h, s_daily] if s > 0)
        bear_4tf = sum(1 for s in [s_5m, s_15m, s_1h, s_daily] if s < 0)

        if bull_4tf == 4:
            confluence_state = "FULL_BULLISH_CONFLUENCE"
            confluence_desc = "All 4 timeframes (5m, 15m, 1H, Daily) in full bullish expansion."
            confluence_color = "text-green"
        elif bear_4tf == 4:
            confluence_state = "FULL_BEARISH_CONFLUENCE"
            confluence_desc = "All 4 timeframes (5m, 15m, 1H, Daily) in full bearish liquidation."
            confluence_color = "text-red"
        elif bull_4tf >= 3:
            confluence_state = "STRONG_BULLISH_ALIGNMENT"
            confluence_desc = f"{bull_4tf} of 4 timeframes aligned bullish. High probability long setups."
            confluence_color = "text-green"
        elif bear_4tf >= 3:
            confluence_state = "STRONG_BEARISH_ALIGNMENT"
            confluence_desc = f"{bear_4tf} of 4 timeframes aligned bearish. High probability short setups."
            confluence_color = "text-red"
        elif s_daily > 0 and s_5m < 0:
            confluence_state = "COUNTER_TREND_PULLBACK_IN_BULL_MARKET"
            confluence_desc = "Tactical 5m pullback inside macro Daily bull market. Watch for VWAP/support bounce."
            confluence_color = "text-cyan"
        elif s_daily < 0 and s_5m > 0:
            confluence_state = "COUNTER_TREND_BOUNCE_IN_BEAR_MARKET"
            confluence_desc = "Tactical 5m bounce inside macro Daily bear market. Watch for resistance fade."
            confluence_color = "text-yellow"
        else:
            confluence_state = "SIDEWAYS_CHOP_CONSOLIDATION"
            confluence_desc = "Timeframes are divergent or range-bound. Capital preservation mode."
            confluence_color = "text-yellow"

        # Overall composite trend
        if bullish_count >= 4:
            composite_trend = "STRONG_BULLISH"
            composite_confidence = 88.0
        elif bullish_count >= 3:
            composite_trend = "BULLISH"
            composite_confidence = 72.0
        elif bearish_count >= 4:
            composite_trend = "STRONG_BEARISH"
            composite_confidence = 88.0
        elif bearish_count >= 3:
            composite_trend = "BEARISH"
            composite_confidence = 72.0
        else:
            composite_trend = "SIDEWAYS_MIXED"
            composite_confidence = 50.0

        four_tf_matrix = {
            "5m": {
                "role": "Tactical Timing & Entry",
                "direction": t_5m.get("direction", "SIDEWAYS"),
                "momentum": t_5m.get("momentum", "NEUTRAL"),
                "confidence": t_5m.get("confidence_pct", 50.0),
                "rsi": t_5m.get("rsi", 50.0),
            },
            "15m": {
                "role": "Intraday Swing Structure",
                "direction": t_15m.get("direction", "SIDEWAYS"),
                "momentum": t_15m.get("momentum", "NEUTRAL"),
                "confidence": t_15m.get("confidence_pct", 50.0),
                "rsi": t_15m.get("rsi", 50.0),
            },
            "1h": {
                "role": "Session Directional Bias",
                "direction": t_1h.get("direction", "SIDEWAYS"),
                "momentum": t_1h.get("momentum", "NEUTRAL"),
                "confidence": t_1h.get("confidence_pct", 50.0),
                "rsi": t_1h.get("rsi", 50.0),
            },
            "daily": {
                "role": "Macro Institutional Regime",
                "direction": t_daily.get("direction", "SIDEWAYS"),
                "momentum": t_daily.get("momentum", "NEUTRAL"),
                "confidence": t_daily.get("confidence_pct", 50.0),
                "rsi": t_daily.get("rsi", 50.0),
            },
        }

        return {
            "timeframes": results,
            "composite_trend": composite_trend,
            "bullish_timeframes": bullish_count,
            "bearish_timeframes": bearish_count,
            "composite_confidence": composite_confidence,
            "institutional_4tf": {
                "confluence_state": confluence_state,
                "confluence_score": norm_score,
                "confluence_desc": confluence_desc,
                "confluence_color": confluence_color,
                "bullish_count": bull_4tf,
                "bearish_count": bear_4tf,
                "matrix": four_tf_matrix,
            },
        }

    @classmethod
    def institutional_4tf(cls, timeframe_suite: Dict[str, pd.DataFrame], spot_price: Optional[float] = None) -> Dict[str, Any]:
        """Convenience method returning the 4-tier institutional confluence matrix with explicit layer projections."""
        res = cls.evaluate_multi_timeframe_suite(timeframe_suite)
        inst = res.get("institutional_4tf", {})
        matrix = inst.get("matrix", {})
        inst["tactical_5m"] = matrix.get("5m", {})
        inst["intraday_swing_15m"] = matrix.get("15m", {})
        inst["session_bias_1h"] = matrix.get("1h", {})
        inst["macro_regime_daily"] = matrix.get("daily", {})
        inst["aligned_score"] = int(inst.get("bullish_count", 0)) - int(inst.get("bearish_count", 0))
        inst["execution_bias"] = "LONG_PRIORITY" if inst["aligned_score"] > 0 else ("SHORT_PRIORITY" if inst["aligned_score"] < 0 else "NEUTRAL")
        return inst
