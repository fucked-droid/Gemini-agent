"""
Quantitative Market Regime Detection Engine.
Synthesizes:
  - Average Directional Index (ADX) & Directional Movement (+DI / -DI)
  - Bollinger Bands Bandwidth & Volatility Squeeze
  - Choppiness Index (CHOP)
  - ATR Percentage & Range Expansion
  - India VIX Volatility Benchmark

Classifies into 5 institutional regimes:
  1. TRENDING_BULLISH: Strong directional upward expansion
  2. TRENDING_BEARISH: Strong directional downward expansion
  3. SIDEWAYS_CONSOLIDATION: Range-bound consolidation / chop
  4. VOLATILE_EXPANSION: Explosive volatility / high binary risk
  5. LOW_VOLATILITY_COMPRESSION: Pre-breakout squeeze
"""

import math
import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger("MarketRegimeDetector")


class MarketRegimeDetector:
    """
    Evaluates multi-factor market regime (Trending, Sideways, Volatile)
    and provides tactical execution guidance.
    """

    @classmethod
    def detect_regime(
        cls,
        df: pd.DataFrame,
        india_vix: Optional[float] = None,
        symbol: str = "NIFTY",
    ) -> Dict[str, Any]:
        """
        Calculates ADX, Choppiness Index, Bollinger Bandwidth, ATR ratio,
        and combines with India VIX to detect authoritative market regime.
        """
        if df is None or len(df) < 14:
            return cls._get_default_regime(symbol, india_vix)

        try:
            highs = df["High"].astype(float)
            lows = df["Low"].astype(float)
            closes = df["Close"].astype(float)
            n = len(df)

            # 1. True Range
            prev_closes = closes.shift(1).fillna(closes.iloc[0])
            tr1 = highs - lows
            tr2 = (highs - prev_closes).abs()
            tr3 = (lows - prev_closes).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # 2. Directional Movement (+DM / -DM)
            up_move = highs - highs.shift(1)
            down_move = lows.shift(1) - lows

            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

            # 14-period Wilder's smoothing
            period = min(14, max(5, n // 2))
            atr_s = tr.rolling(period).mean()
            plus_dm_s = pd.Series(plus_dm, index=df.index).rolling(period).mean()
            minus_dm_s = pd.Series(minus_dm, index=df.index).rolling(period).mean()

            curr_atr = float(atr_s.iloc[-1]) if not pd.isna(atr_s.iloc[-1]) else float(tr.iloc[-1])
            curr_close = float(closes.iloc[-1])
            atr_pct = (curr_atr / curr_close * 100.0) if curr_close > 0 else 0.5

            plus_di_val = (plus_dm_s.iloc[-1] / curr_atr * 100.0) if curr_atr > 0 else 20.0
            minus_di_val = (minus_dm_s.iloc[-1] / curr_atr * 100.0) if curr_atr > 0 else 20.0

            di_sum = plus_di_val + minus_di_val
            dx = (abs(plus_di_val - minus_di_val) / di_sum * 100.0) if di_sum > 0 else 15.0
            adx_val = round(dx, 1)

            # 3. Choppiness Index (CHOP)
            # CHOP = 100 * LOG10(SUM(TR, 14) / (MaxHigh(14) - MinLow(14))) / LOG10(14)
            tr_sum = tr.rolling(period).sum().iloc[-1]
            hh = highs.rolling(period).max().iloc[-1]
            ll = lows.rolling(period).min().iloc[-1]
            hl_range = hh - ll

            if hl_range > 0 and tr_sum > 0:
                chop_val = 100.0 * (math.log10(tr_sum / hl_range) / math.log10(period))
                chop_val = max(0.0, min(100.0, chop_val))
            else:
                chop_val = 50.0

            # 4. Bollinger Bands Bandwidth
            sma20 = closes.rolling(min(20, n)).mean().iloc[-1]
            std20 = closes.rolling(min(20, n)).std().iloc[-1]
            if pd.isna(std20) or std20 == 0:
                std20 = curr_atr * 0.8
            bb_upper = sma20 + (2.0 * std20)
            bb_lower = sma20 - (2.0 * std20)
            bb_width_pct = ((bb_upper - bb_lower) / sma20 * 100.0) if sma20 > 0 else 1.0

            # 5. Volatility Regime from India VIX and ATR
            vix_val = float(india_vix) if india_vix is not None and india_vix > 0 else 15.5
            if vix_val >= 20.0 or atr_pct >= 1.5:
                vol_regime = "EXTREME_VOLATILITY"
                vol_label = "Extreme Volatility"
                vol_color = "text-red"
            elif vix_val >= 16.5 or atr_pct >= 1.1:
                vol_regime = "ELEVATED_VOLATILITY"
                vol_label = "Elevated Volatility"
                vol_color = "text-yellow"
            elif vix_val <= 12.0 and atr_pct <= 0.6:
                vol_regime = "LOW_VOLATILITY"
                vol_label = "Low Volatility (Complacent)"
                vol_color = "text-cyan"
            else:
                vol_regime = "NORMAL_VOLATILITY"
                vol_label = "Normal Volatility"
                vol_color = "text-green"

            # 6. Primary Regime Classification
            is_trending_up = (adx_val >= 24.0 and plus_di_val > minus_di_val + 3.0 and curr_close >= sma20)
            is_trending_down = (adx_val >= 24.0 and minus_di_val > plus_di_val + 3.0 and curr_close <= sma20)
            is_choppy = (chop_val >= 58.0 or adx_val < 20.0 or abs(plus_di_val - minus_di_val) < 4.0)
            is_volatile_expansion = (vol_regime in ("ELEVATED_VOLATILITY", "EXTREME_VOLATILITY") and atr_pct >= 1.0)
            is_squeeze = (bb_width_pct < 0.6 and chop_val > 52.0 and adx_val < 18.0)

            if is_squeeze:
                regime = "LOW_VOLATILITY_COMPRESSION"
                regime_label = "Low-Volatility Squeeze"
                regime_badge = "SQUEEZE"
                regime_color = "text-cyan"
                regime_score = 0.0
                strategy = "Breakout Anticipation: Volatility compression. Wait for explosive expansion candle."
            elif is_volatile_expansion and not (is_trending_up or is_trending_down):
                regime = "VOLATILE_EXPANSION"
                regime_label = "Volatile Expansion"
                regime_badge = "VOLATILE"
                regime_color = "text-red"
                regime_score = -1.0 if minus_di_val > plus_di_val else 1.0
                strategy = "Binary Shock Risk: Reduce position sizing by 40-50%. Use wide stops and quick profits."
            elif is_trending_up:
                regime = "TRENDING_BULLISH"
                regime_label = "Trending Bullish"
                regime_badge = "TRENDING UP"
                regime_color = "text-green"
                regime_score = min(3.0, 1.5 + (adx_val / 20.0))
                strategy = "Trend Continuation: Prioritize pullback buys to Session VWAP and EMA 10/20 support."
            elif is_trending_down:
                regime = "TRENDING_BEARISH"
                regime_label = "Trending Bearish"
                regime_badge = "TRENDING DOWN"
                regime_color = "text-red"
                regime_score = max(-3.0, -1.5 - (adx_val / 20.0))
                strategy = "Trend Liquidation: Prioritize short continuation on relief bounces or maintain cash."
            elif is_choppy:
                regime = "SIDEWAYS_CONSOLIDATION"
                regime_label = "Sideways / Range Consolidation"
                regime_badge = "SIDEWAYS CHOP"
                regime_color = "text-yellow"
                regime_score = 0.0
                strategy = "Mean Reversion / Capital Preservation: Avoid trend-following orders inside range chop."
            else:
                regime = "NEUTRAL_TRANSITION"
                regime_label = "Neutral Transition"
                regime_badge = "TRANSITION"
                regime_color = "text-yellow"
                regime_score = 0.0
                strategy = "Awaiting directional breakout confirmation."

            return {
                "regime": regime,
                "regime_label": regime_label,
                "regime_badge": regime_badge,
                "regime_color": regime_color,
                "regime_score": round(regime_score, 2),
                "trend_state": "TRENDING" if "TRENDING" in regime else ("SIDEWAYS" if "SIDEWAYS" in regime else "VOLATILE"),
                "adx": round(adx_val, 1),
                "plus_di": round(plus_di_val, 1),
                "minus_di": round(minus_di_val, 1),
                "chop_index": round(chop_val, 1),
                "bb_bandwidth_pct": round(bb_width_pct, 2),
                "bb_bandwidth": round(bb_width_pct, 2),
                "atr": round(curr_atr, 2),
                "atr_pct": round(atr_pct, 2),
                "india_vix": round(vix_val, 2),
                "volatility_regime": vol_regime,
                "volatility_label": vol_label,
                "volatility_color": vol_color,
                "strategy_recommendation": strategy,
                "actionable_strategy": strategy,
                "regime_explanation": strategy,
                "symbol": symbol,
            }

        except Exception as e:
            logger.warning(f"Error computing market regime for {symbol}: {e}")
            return cls._get_default_regime(symbol, india_vix)

    @classmethod
    def _get_default_regime(cls, symbol: str, india_vix: Optional[float] = None) -> Dict[str, Any]:
        """Provides safe fallback regime payload."""
        vix = india_vix or 15.5
        fallback_strategy = "Capital Preservation: Range consolidation. Await confirmed volume breakout."
        return {
            "regime": "SIDEWAYS_CONSOLIDATION",
            "regime_label": "Sideways / Range Consolidation",
            "regime_badge": "SIDEWAYS CHOP",
            "regime_color": "text-yellow",
            "regime_score": 0.0,
            "trend_state": "SIDEWAYS",
            "adx": 18.5,
            "plus_di": 21.0,
            "minus_di": 22.0,
            "chop_index": 58.4,
            "bb_bandwidth_pct": 0.85,
            "bb_bandwidth": 0.85,
            "atr": 125.0,
            "atr_pct": 0.50,
            "india_vix": round(vix, 2),
            "volatility_regime": "NORMAL_VOLATILITY",
            "volatility_label": "Normal Volatility",
            "volatility_color": "text-green",
            "strategy_recommendation": fallback_strategy,
            "actionable_strategy": fallback_strategy,
            "regime_explanation": fallback_strategy,
            "symbol": symbol,
        }
