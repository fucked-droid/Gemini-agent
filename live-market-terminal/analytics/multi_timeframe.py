"""
Multi-Timeframe Market Analysis Engine.
Analyzes 1m, 5m, 15m, 30m, and 60m candles for:
- Trend direction (Bullish, Bearish, Sideways)
- Momentum (RSI + MACD Histogram)
- EMA alignment (EMA 10 vs EMA 20)
- VWAP positioning (Above/Below)
- Volume confirmation
- Explicitly quantified signal confidence (0-100%)
"""

import logging
from typing import Dict, Any
import pandas as pd
import numpy as np

from .indicators import TechnicalIndicators

logger = logging.getLogger("MultiTimeframeEngine")

class MultiTimeframeEngine:
    """
    Evaluates individual timeframes and synthesizes multi-timeframe alignment.
    """

    @classmethod
    def analyze_single_timeframe(cls, df: pd.DataFrame, timeframe_label: str) -> Dict[str, Any]:
        """
        Analyzes a single timeframe's indicators and scores its directional state.
        """
        if df.empty or len(df) < 5:
            return {
                "timeframe": timeframe_label,
                "direction": "SIDEWAYS",
                "momentum": "NEUTRAL",
                "ema_alignment": "NEUTRAL",
                "vwap_position": "AT_VWAP",
                "volume_confirmed": False,
                "confidence_pct": 50.0,
                "bias_score": 0.0,
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

        # VWAP Position
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
        if rsi > 55 and macd_hist > 0:
            momentum = "BULLISH_EXPANSION"
            mom_score = 1.0
        elif rsi < 45 and macd_hist < 0:
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
        vol = df["Volume"].iloc[-1]
        avg_vol = df["Volume"].tail(10).mean()
        vol_confirmed = bool(vol >= avg_vol * 0.9)
        vol_score = 0.5 if vol_confirmed else 0.0

        # Composite Timeframe Bias (-3.0 to +3.0)
        raw_score = ema_score + vwap_score + mom_score
        if raw_score >= 1.5:
            direction = "BULLISH"
        elif raw_score <= -1.5:
            direction = "BEARISH"
        else:
            direction = "SIDEWAYS"

        # Explicitly calibrated confidence (50% to 95%)
        # Base confidence from magnitude of alignment + volume confirmation bonus
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
        cls, timeframe_suite: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """
        Runs analysis across 1m, 5m, 15m, 30m, 60m and computes cross-timeframe alignment.
        """
        results = {}
        timeframes = ["1m", "5m", "15m", "30m", "60m"]
        bullish_count = 0
        bearish_count = 0

        for tf in timeframes:
            df = timeframe_suite.get(tf, pd.DataFrame())
            res = cls.analyze_single_timeframe(df, tf)
            results[tf] = res
            if res["direction"] == "BULLISH":
                bullish_count += 1
            elif res["direction"] == "BEARISH":
                bearish_count += 1

        # Multi-timeframe synthesis
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

        return {
            "timeframes": results,
            "composite_trend": composite_trend,
            "bullish_timeframes": bullish_count,
            "bearish_timeframes": bearish_count,
            "composite_confidence": composite_confidence,
        }
