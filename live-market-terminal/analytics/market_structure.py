"""
Market Structure & Price Action Analytics Engine.
Identifies fractal swing highs/lows, higher-highs/lower-lows sequences,
Break of Structure (BOS), Change of Character (CHoCH), and dynamic Support/Resistance levels.
"""

import logging
from typing import Dict, Any, List
import pandas as pd
import numpy as np

logger = logging.getLogger("MarketStructureAnalyzer")

class MarketStructureAnalyzer:
    """
    Price Action and Institutional Market Structure Engine.
    """

    @staticmethod
    def find_swings(df: pd.DataFrame, window: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detects fractal Swing Highs and Swing Lows with an N-bar lookback/lookahead window.
        """
        if df.empty or len(df) < (2 * window + 1):
            return {"swing_highs": [], "swing_lows": []}

        highs = []
        lows = []

        for i in range(window, len(df) - window):
            curr_high = df["High"].iloc[i]
            curr_low = df["Low"].iloc[i]
            curr_time = str(df.index[i])

            # Is swing high?
            is_sh = True
            for w in range(1, window + 1):
                if df["High"].iloc[i - w] >= curr_high or df["High"].iloc[i + w] >= curr_high:
                    is_sh = False
                    break
            if is_sh:
                highs.append({"price": float(curr_high), "timestamp": curr_time, "index": i})

            # Is swing low?
            is_sl = True
            for w in range(1, window + 1):
                if df["Low"].iloc[i - w] <= curr_low or df["Low"].iloc[i + w] <= curr_low:
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
        if df.empty or len(df) < 10:
            return {
                "structure_state": "NEUTRAL_CONSOLIDATION",
                "trend_type": "SIDEWAYS",
                "event": "NO_STRUCTURE_EVENT",
                "nearest_support": 0.0,
                "nearest_resistance": 0.0,
                "swing_highs": [],
                "swing_lows": [],
            }

        swings = cls.find_swings(df, window=2)
        sh_list = swings["swing_highs"]
        sl_list = swings["swing_lows"]
        current_price = float(df["Close"].iloc[-1])

        # Default fallback support and resistance from recent extremes
        recent_high = float(df["High"].tail(20).max())
        recent_low = float(df["Low"].tail(20).min())

        nearest_res = recent_high
        nearest_sup = recent_low

        if sh_list:
            res_candidates = [s["price"] for s in sh_list if s["price"] > current_price]
            if res_candidates:
                nearest_res = min(res_candidates)
            else:
                nearest_res = max([s["price"] for s in sh_list])

        if sl_list:
            sup_candidates = [s["price"] for s in sl_list if s["price"] < current_price]
            if sup_candidates:
                nearest_sup = max(sup_candidates)
            else:
                nearest_sup = min([s["price"] for s in sl_list])

        # Sequence determination
        structure_state = "NEUTRAL_CONSOLIDATION"
        event = "NONE"

        if len(sh_list) >= 2 and len(sl_list) >= 2:
            prev_sh, last_sh = sh_list[-2]["price"], sh_list[-1]["price"]
            prev_sl, last_sl = sl_list[-2]["price"], sl_list[-1]["price"]

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

        return {
            "structure_state": structure_state,
            "trend_type": trend_type,
            "event": event,
            "nearest_support": round(nearest_sup, 2),
            "nearest_resistance": round(nearest_res, 2),
            "swing_highs": [round(s["price"], 2) for s in sh_list[-3:]],
            "swing_lows": [round(s["price"], 2) for s in sl_list[-3:]],
        }
