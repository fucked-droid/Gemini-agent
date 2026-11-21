"""
Market Structure & Price Action Analytics Engine.
Identifies fractal swing highs/lows, higher-highs/lower-lows sequences,
Break of Structure (BOS), Change of Character (CHoCH), and dynamic Support/Resistance levels.
"""

import logging
import math
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger("MarketStructureAnalyzer")

class MarketStructureAnalyzer:
    """
    Price Action and Institutional Market Structure Engine.
    """

    @staticmethod
    def validate_ohlc_dataframe(df: pd.DataFrame, min_bars: int = 10) -> Optional[str]:
        """
        Validates OHLC candle data integrity before computing market structure:
        - Rejects None, non-DataFrame objects, or empty DataFrames.
        - Rejects DataFrames with fewer than min_bars candles ("INSUFFICIENT HISTORICAL DATA").
        - Requires 'Open', 'High', 'Low', 'Close' numeric columns.
        - Rejects null, undefined, NaN, or infinite price values.
        - Rejects invalid pricing rules (e.g. price <= 0, High < Low).
        Returns None if valid, or an error string ("INSUFFICIENT HISTORICAL DATA", "UNAVAILABLE — INVALID INPUT DATA").
        """
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return "INSUFFICIENT HISTORICAL DATA"

        required_cols = ["Open", "High", "Low", "Close"]
        if not all(col in df.columns for col in required_cols):
            return "UNAVAILABLE — INVALID INPUT DATA"

        if len(df) < min_bars:
            return "INSUFFICIENT HISTORICAL DATA"

        sub_df = df[required_cols]

        # Check for null, NaN, or infinite values
        if sub_df.isnull().any().any():
            return "UNAVAILABLE — INVALID INPUT DATA"

        # Check for numeric type and non-infinite values
        try:
            vals = sub_df.to_numpy(dtype=float)
            if not np.isfinite(vals).all():
                return "UNAVAILABLE — INVALID INPUT DATA"
            if (vals <= 0).any():
                return "UNAVAILABLE — INVALID INPUT DATA"
        except (ValueError, TypeError):
            return "UNAVAILABLE — INVALID INPUT DATA"

        # Check basic OHLC logical consistency: High >= Low
        highs = sub_df["High"].to_numpy(dtype=float)
        lows = sub_df["Low"].to_numpy(dtype=float)
        if (highs < lows).any():
            return "UNAVAILABLE — INVALID INPUT DATA"

        return None

    @classmethod
    def find_swings(cls, df: pd.DataFrame, window: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detects fractal Swing Highs and Swing Lows with an N-bar lookback/lookahead window.
        """
        validation_err = cls.validate_ohlc_dataframe(df, min_bars=(2 * window + 1))
        if validation_err:
            return {"swing_highs": [], "swing_lows": []}

        highs = []
        lows = []

        for i in range(window, len(df) - window):
            curr_high = float(df["High"].iloc[i])
            curr_low = float(df["Low"].iloc[i])
            curr_time = str(df.index[i])

            if not math.isfinite(curr_high) or not math.isfinite(curr_low):
                continue

            # Is swing high?
            is_sh = True
            for w in range(1, window + 1):
                prev_h = float(df["High"].iloc[i - w])
                next_h = float(df["High"].iloc[i + w])
                if prev_h >= curr_high or next_h >= curr_high:
                    is_sh = False
                    break
            if is_sh:
                highs.append({"price": float(curr_high), "timestamp": curr_time, "index": i})

            # Is swing low?
            is_sl = True
            for w in range(1, window + 1):
                prev_l = float(df["Low"].iloc[i - w])
                next_l = float(df["Low"].iloc[i + w])
                if prev_l <= curr_low or next_l <= curr_low:
                    is_sl = False
                    break
            if is_sl:
                lows.append({"price": float(curr_low), "timestamp": curr_time, "index": i})

        return {"swing_highs": highs, "swing_lows": lows}

    @classmethod
    def analyze_structure(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Classifies overall market structure:
        - BULLISH_EXPANSION (HH + HL)
        - BEARISH_EXPANSION (LH + LL)
        - CONSOLIDATION_RANGE (Mixed / Inside)
        - BOS (Break of Structure) or CHoCH (Change of Character)
        """
        validation_err = cls.validate_ohlc_dataframe(df, min_bars=10)
        if validation_err:
            return {
                "status": validation_err,
                "structure_state": "NEUTRAL_CONSOLIDATION",
                "trend_type": "SIDEWAYS",
                "event": "NO_STRUCTURE_EVENT",
                "nearest_support": 0.0,
                "nearest_resistance": 0.0,
                "swing_highs": [],
                "swing_lows": [],
                "error_message": validation_err,
            }

        try:
            swings = cls.find_swings(df, window=2)
            sh_list = swings["swing_highs"]
            sl_list = swings["swing_lows"]
            current_price = float(df["Close"].iloc[-1])

            if not math.isfinite(current_price) or current_price <= 0:
                return {
                    "status": "UNAVAILABLE — INVALID INPUT DATA",
                    "structure_state": "NEUTRAL_CONSOLIDATION",
                    "trend_type": "SIDEWAYS",
                    "event": "NO_STRUCTURE_EVENT",
                    "nearest_support": 0.0,
                    "nearest_resistance": 0.0,
                    "swing_highs": [],
                    "swing_lows": [],
                    "error_message": "UNAVAILABLE — INVALID INPUT DATA",
                }

            # Support and resistance from recent extremes
            recent_high = float(df["High"].tail(20).max())
            recent_low = float(df["Low"].tail(20).min())

            nearest_res = recent_high
            nearest_sup = recent_low

            if sh_list:
                res_candidates = [s["price"] for s in sh_list if s["price"] > current_price and math.isfinite(s["price"])]
                if res_candidates:
                    nearest_res = min(res_candidates)
                else:
                    valid_sh = [s["price"] for s in sh_list if math.isfinite(s["price"])]
                    if valid_sh:
                        nearest_res = max(valid_sh)

            if sl_list:
                sup_candidates = [s["price"] for s in sl_list if s["price"] < current_price and math.isfinite(s["price"])]
                if sup_candidates:
                    nearest_sup = max(sup_candidates)
                else:
                    valid_sl = [s["price"] for s in sl_list if math.isfinite(s["price"])]
                    if valid_sl:
                        nearest_sup = min(valid_sl)

            # Sequence determination
            structure_state = "NEUTRAL_CONSOLIDATION"
            event = "NONE"

            if len(sh_list) >= 2 and len(sl_list) >= 2:
                prev_sh, last_sh = sh_list[-2]["price"], sh_list[-1]["price"]
                prev_sl, last_sl = sl_list[-2]["price"], sl_list[-1]["price"]

                if all(math.isfinite(p) and p > 0 for p in [prev_sh, last_sh, prev_sl, last_sl]):
                    if last_sh > prev_sh and last_sl > prev_sl:
                        structure_state = "BULLISH_EXPANSION"
                        trend_type = "BULLISH"
                        if current_price > last_sh:
                            event = "BOS_BULLISH_CONTINUATION"
                    elif last_sh < prev_sh and last_sl < prev_sl:
                        structure_state = "BEARISH_EXPANSION"
                        trend_type = "BEARISH"
                        if current_price < last_sl:
                            event = "BOS_BEARISH_CONTINUATION"
                    elif last_sh > prev_sh and last_sl < prev_sl:
                        structure_state = "BROADENING_RANGE"
                        trend_type = "SIDEWAYS"
                        event = "VOLATILITY_EXPANSION"
                    else:
                        structure_state = "COMPRESSION_TRIANGLE"
                        trend_type = "SIDEWAYS"
                        event = "RANGE_CONTRACTION"
                else:
                    trend_type = "SIDEWAYS"
            else:
                trend_type = "SIDEWAYS"

            return {
                "status": "VALID",
                "structure_state": structure_state,
                "trend_type": trend_type,
                "event": event,
                "nearest_support": round(nearest_sup, 2) if math.isfinite(nearest_sup) else 0.0,
                "nearest_resistance": round(nearest_res, 2) if math.isfinite(nearest_res) else 0.0,
                "swing_highs": [round(s["price"], 2) for s in sh_list[-3:] if math.isfinite(s["price"])],
                "swing_lows": [round(s["price"], 2) for s in sl_list[-3:] if math.isfinite(s["price"])],
            }
        except Exception as e:
            logger.error(f"Error analyzing market structure: {e}")
            return {
                "status": "UNAVAILABLE — INVALID INPUT DATA",
                "structure_state": "NEUTRAL_CONSOLIDATION",
                "trend_type": "SIDEWAYS",
                "event": "NO_STRUCTURE_EVENT",
                "nearest_support": 0.0,
                "nearest_resistance": 0.0,
                "swing_highs": [],
                "swing_lows": [],
                "error_message": "UNAVAILABLE — INVALID INPUT DATA",
            }

