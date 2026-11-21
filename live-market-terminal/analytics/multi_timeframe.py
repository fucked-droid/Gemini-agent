"""
Multi-Timeframe Market Analysis Engine.
Analyzes 1m, 5m, 15m, 30m, 60m, and Daily candles for:
- Price Structure & Swing high/low direction
- EMA alignment (EMA 10 vs EMA 20) and slope
- Momentum (RSI + MACD Histogram)
- Trend Strength via Welles Wilder ADX
- Session VWAP positioning (Above/Below)
- Multi-indicator agreement & calibrated trend strength
- Structured Sub-tier Alignment: Short-Term (1m+5m), Intraday (15m+30m+60m), Macro (Daily)
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
        Analyzes a single timeframe's indicators and scores its directional state
        using a consistent multi-factor methodology:
        1. Price Structure & Swings (recent 10-bar high/low breakout)
        2. EMA 10 vs EMA 20 alignment and slope
        3. Momentum (RSI + MACD histogram)
        4. Session VWAP positioning
        5. Trend Strength via Welles Wilder ADX
        """
        if df is None or df.empty or len(df) < 5:
            return {
                "timeframe": timeframe_label,
                "direction": "UNAVAILABLE",
                "momentum": "UNAVAILABLE",
                "ema_alignment": "UNAVAILABLE",
                "vwap_position": "UNAVAILABLE",
                "trend_strength_pct": 0.0,
                "trend_strength_label": "NO DATA",
                "indicator_agreement": "0/4",
                "adx": 0.0,
                "adx_state": "UNAVAILABLE",
                "bias_score": 0.0,
                "close": 0.0,
                "vwap": 0.0,
                "ema10": 0.0,
                "ema20": 0.0,
                "rsi": 50.0,
                "last_candle_time": "--",
            }

        df_ind, sc = TechnicalIndicators.calculate_all(df)
        close = sc["close"]
        ema10 = sc["ema10"]
        ema20 = sc["ema20"]
        vwap = sc["vwap"]
        rsi = sc["rsi"]
        macd_hist = sc["macd_hist"]

        # ADX trend strength calculation
        adx_series, pos_di, neg_di = TechnicalIndicators.compute_adx(df, period=14)
        latest_adx = float(adx_series.dropna().iloc[-1]) if not adx_series.dropna().empty else 15.0
        latest_pdi = float(pos_di.dropna().iloc[-1]) if not pos_di.dropna().empty else 20.0
        latest_ndi = float(neg_di.dropna().iloc[-1]) if not neg_di.dropna().empty else 20.0

        if latest_adx >= 30.0:
            adx_state = "STRONG_TREND"
        elif latest_adx >= 20.0:
            adx_state = "MODERATE_TREND"
        else:
            adx_state = "RANGE_BOUND"

        # Factor 1: EMA Alignment & Slope
        if ema10 > ema20 * 1.0003:
            ema_align = "BULLISH_STACK"
            ema_dir = 1
        elif ema10 < ema20 * 0.9997:
            ema_align = "BEARISH_STACK"
            ema_dir = -1
        else:
            ema_align = "COMPRESSED"
            ema_dir = 0

        # Factor 2: VWAP Position
        if close > vwap * 1.0003:
            vwap_pos = "ABOVE_VWAP"
            vwap_dir = 1
        elif close < vwap * 0.9997:
            vwap_pos = "BELOW_VWAP"
            vwap_dir = -1
        else:
            vwap_pos = "AT_VWAP"
            vwap_dir = 0

        # Factor 3: Momentum (RSI + MACD Hist)
        if rsi > 52.0 and macd_hist >= 0:
            momentum = "BULLISH_EXPANSION"
            mom_dir = 1
        elif rsi < 48.0 and macd_hist <= 0:
            momentum = "BEARISH_EXPANSION"
            mom_dir = -1
        else:
            momentum = "NEUTRAL"
            mom_dir = 0

        # Factor 4: Price Structure / Swing Breakout (last 10 bars)
        lookback = min(10, len(df))
        prev_bars = df.iloc[-lookback:-1] if len(df) > lookback else df.iloc[:-1]
        if not prev_bars.empty:
            swing_h = prev_bars["High"].max()
            swing_l = prev_bars["Low"].min()
            if close >= swing_h * 0.9998:
                struct_dir = 1
            elif close <= swing_l * 1.0002:
                struct_dir = -1
            else:
                struct_dir = 0
        else:
            struct_dir = 0

        # Indicator Agreement Count (out of 4 core factors)
        bull_agree = sum(1 for d in [ema_dir, vwap_dir, mom_dir, struct_dir] if d > 0)
        bear_agree = sum(1 for d in [ema_dir, vwap_dir, mom_dir, struct_dir] if d < 0)

        # Calibrated Trend Direction & Strength
        if bull_agree >= 3 and latest_pdi >= latest_ndi:
            direction = "BULLISH"
            trend_strength_pct = round(min(98.0, 50.0 + (bull_agree / 4.0) * 30.0 + (latest_adx * 0.6)), 1)
            agreement_str = f"{bull_agree}/4 Bullish"
        elif bear_agree >= 3 and latest_ndi >= latest_pdi:
            direction = "BEARISH"
            trend_strength_pct = round(min(98.0, 50.0 + (bear_agree / 4.0) * 30.0 + (latest_adx * 0.6)), 1)
            agreement_str = f"{bear_agree}/4 Bearish"
        else:
            direction = "SIDEWAYS"
            trend_strength_pct = round(max(20.0, 50.0 - (latest_adx * 0.5)), 1)
            agreement_str = f"Mixed ({bull_agree}B / {bear_agree}S)"

        if trend_strength_pct >= 75.0:
            trend_strength_label = "HIGH STRENGTH"
        elif trend_strength_pct >= 55.0:
            trend_strength_label = "MODERATE"
        else:
            trend_strength_label = "CHOPPY / WEAK"

        # Timestamp of last candle
        last_ts_str = str(df.index[-1]) if isinstance(df.index, pd.DatetimeIndex) and not df.empty else "--"

        return {
            "timeframe": timeframe_label,
            "direction": direction,
            "momentum": momentum,
            "ema_alignment": ema_align,
            "vwap_position": vwap_pos,
            "trend_strength_pct": trend_strength_pct,
            "trend_strength_label": trend_strength_label,
            "indicator_agreement": agreement_str,
            "adx": round(latest_adx, 1),
            "adx_state": adx_state,
            "bias_score": round(float(bull_agree - bear_agree), 1),
            "close": close,
            "vwap": vwap,
            "ema10": ema10,
            "ema20": ema20,
            "rsi": rsi,
            "last_candle_time": last_ts_str,
        }

    @classmethod
    def evaluate_multi_timeframe_suite(
        cls,
        timeframe_suite: Dict[str, pd.DataFrame],
        daily_df: Optional[pd.DataFrame] = None,
        symbol: str = "NIFTY",
    ) -> Dict[str, Any]:
        """
        Runs comprehensive multi-timeframe analysis across 6 distinct timeframes
        (1m, 5m, 15m, 30m, 60m, daily) and synthesizes layered tier alignments:
        - Short-Term: 1m & 5m alignment
        - Intraday: 15m, 30m & 60m alignment
        - Higher Timeframe: Daily trend
        - Overall Alignment: Bullish / Bearish / Mixed / Sideways / Unavailable
        """
        results = {}
        standard_tfs = ["1m", "5m", "15m", "30m", "60m"]

        for tf in standard_tfs:
            df = timeframe_suite.get(tf, pd.DataFrame())
            results[tf] = cls.analyze_single_timeframe(df, tf)

        # Evaluate Daily Macro Timeframe
        df_daily = daily_df if daily_df is not None and not daily_df.empty else timeframe_suite.get("daily", pd.DataFrame())
        if df_daily.empty:
            df_daily = timeframe_suite.get("1d", pd.DataFrame())

        results["daily"] = cls.analyze_single_timeframe(df_daily, "daily")

        # -------------------------------------------------------------
        # Tiered Aggregation Logic
        # -------------------------------------------------------------
        t_1m = results.get("1m", {})
        t_5m = results.get("5m", {})
        t_15m = results.get("15m", {})
        t_30m = results.get("30m", {})
        t_60m = results.get("60m", {})
        t_daily = results.get("daily", {})

        # 1. Short-Term Alignment (1m & 5m)
        st_dirs = [t_1m.get("direction"), t_5m.get("direction")]
        if st_dirs == ["BULLISH", "BULLISH"]:
            short_term_alignment = "BULLISH"
        elif st_dirs == ["BEARISH", "BEARISH"]:
            short_term_alignment = "BEARISH"
        elif "BULLISH" in st_dirs and "BEARISH" in st_dirs:
            short_term_alignment = "CONFLICTED"
        else:
            short_term_alignment = "SIDEWAYS"

        # 2. Intraday Alignment (15m, 30m, 60m)
        intra_dirs = [t_15m.get("direction"), t_30m.get("direction"), t_60m.get("direction")]
        intra_bull = intra_dirs.count("BULLISH")
        intra_bear = intra_dirs.count("BEARISH")
        if intra_bull >= 2 and intra_bear == 0:
            intraday_alignment = "BULLISH"
        elif intra_bear >= 2 and intra_bull == 0:
            intraday_alignment = "BEARISH"
        elif intra_bull >= 1 and intra_bear >= 1:
            intraday_alignment = "MIXED"
        else:
            intraday_alignment = "SIDEWAYS"

        # 3. Higher Timeframe Alignment (Daily)
        htf_alignment = t_daily.get("direction", "SIDEWAYS")

        # 4. Overall Confluence & Explanation
        all_dirs = [t.get("direction") for t in results.values()]
        total_bull = all_dirs.count("BULLISH")
        total_bear = all_dirs.count("BEARISH")
        total_side = all_dirs.count("SIDEWAYS")

        if total_bull >= 5:
            overall_alignment = "STRONG BULLISH"
            alignment_explanation = "5+ timeframes in strong directional upward alignment."
        elif total_bear >= 5:
            overall_alignment = "STRONG BEARISH"
            alignment_explanation = "5+ timeframes in strong directional downward alignment."
        elif short_term_alignment == "BULLISH" and intraday_alignment == "BULLISH" and htf_alignment == "BULLISH":
            overall_alignment = "BULLISH CONFLUENCE"
            alignment_explanation = "Short-term, intraday, and daily trends are fully aligned bullish."
        elif short_term_alignment == "BEARISH" and intraday_alignment == "BEARISH" and htf_alignment == "BEARISH":
            overall_alignment = "BEARISH CONFLUENCE"
            alignment_explanation = "Short-term, intraday, and daily trends are fully aligned bearish."
        elif short_term_alignment == "BULLISH" and htf_alignment in ("SIDEWAYS", "BEARISH"):
            overall_alignment = "MIXED (ST RALLY vs HTF RANGE)"
            alignment_explanation = "Tactical 1m/5m bounce conflicting with higher timeframe consolidation."
        elif short_term_alignment == "BEARISH" and htf_alignment in ("SIDEWAYS", "BULLISH"):
            overall_alignment = "MIXED (ST PULLBACK in HTF BULL)"
            alignment_explanation = "Tactical 1m/5m pullback testing intraday value inside macro trend."
        elif total_side >= 4:
            overall_alignment = "SIDEWAYS CHOP"
            alignment_explanation = "4+ timeframes lack directional expansion. Range-bound price action."
        else:
            overall_alignment = "DIVERGENT MIXED"
            alignment_explanation = f"Divergence across tiers ({total_bull} Bull / {total_bear} Bear / {total_side} Range)."

        # Institutional 4-Tier Confluence (5m, 15m, 1H, Daily)
        bull_4tf = sum(1 for tf in ["5m", "15m", "60m", "daily"] if results.get(tf, {}).get("direction") == "BULLISH")
        bear_4tf = sum(1 for tf in ["5m", "15m", "60m", "daily"] if results.get(tf, {}).get("direction") == "BEARISH")

        return {
            "symbol": symbol,
            "timeframes": results,
            "composite_trend": overall_alignment,
            "composite_confidence": round(float(np.mean([t.get("trend_strength_pct", 50.0) for t in results.values()])), 1),
            "bullish_timeframes": total_bull,
            "bearish_timeframes": total_bear,
            "tiered_alignment": {
                "short_term": short_term_alignment,
                "intraday": intraday_alignment,
                "higher_timeframe": htf_alignment,
                "overall": overall_alignment,
                "explanation": alignment_explanation,
            },
            "institutional_4tf": {
                "confluence_state": overall_alignment,
                "confluence_score": round((total_bull - total_bear) / 6.0 * 2.0, 2),
                "confluence_desc": alignment_explanation,
                "bullish_count": bull_4tf,
                "bearish_count": bear_4tf,
                "matrix": {
                    "5m": t_5m,
                    "15m": t_15m,
                    "1h": t_60m,
                    "daily": t_daily,
                },
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

