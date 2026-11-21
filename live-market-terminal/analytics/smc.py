"""
Smart Money Concepts (SMC) & Institutional Price Delivery Engine.
Implements:
1. Liquidity Sweeps & Stop Hunts (Buy-Side Liquidity BSL & Sell-Side Liquidity SSL).
2. Fair Value Gaps (FVG / Imbalances) & Consequent Encroachment (CE).
3. Institutional Order Blocks (OB) & Mean Threshold (MT).
4. Market Structure Shift (MSS / CHoCH) & Break of Structure (BOS).
5. Fixed Structural Entry Point computation (anchored to institutional price levels).
6. Comprehensive Why-It-Works breakdown and Reversal Threat / Invalidation Risk analysis.
"""

import logging
import math
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from analytics.market_structure import MarketStructureAnalyzer

logger = logging.getLogger("SMCAnalyzer")

class SMCAnalyzer:
    """
    Mathematical and Structural Smart Money Concepts Engine.
    """

    @staticmethod
    def validate_ohlc_dataframe(df: pd.DataFrame, min_bars: int = 10) -> Optional[str]:
        """
        Validates OHLC candle data integrity before calculating BOS, CHoCH,
        liquidity sweeps, order blocks, and FVGs:
        1. Reject null, undefined, NaN, and infinite price values.
        2. Reject non-positive price values or inconsistent ranges (High < Low).
        3. Returns 'INSUFFICIENT HISTORICAL DATA' if rows < min_bars.
        4. Returns 'UNAVAILABLE — INVALID INPUT DATA' if corrupted or calculation fails.
        """
        return MarketStructureAnalyzer.validate_ohlc_dataframe(df, min_bars=min_bars)

    @classmethod
    def detect_fair_value_gaps(cls, df: pd.DataFrame, min_gap_pct: float = 0.0003) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detects 3-candle Fair Value Gaps (FVG) and tracks their mitigation status.
        - Bullish FVG: High[candle i-2] < Low[candle i]
        - Bearish FVG: Low[candle i-2] > High[candle i]
        """
        validation_err = cls.validate_ohlc_dataframe(df, min_bars=3)
        if validation_err:
            return {"bullish_fvgs": [], "bearish_fvgs": [], "status": validation_err}

        bullish_fvgs = []
        bearish_fvgs = []
        n = len(df)
        current_price = float(df["Close"].iloc[-1])

        for i in range(2, n):
            c0_high = float(df["High"].iloc[i - 2])
            c0_low = float(df["Low"].iloc[i - 2])
            c2_high = float(df["High"].iloc[i])
            c2_low = float(df["Low"].iloc[i])
            c1_time = str(df.index[i - 1])

            if not all(math.isfinite(x) and x > 0 for x in [c0_high, c0_low, c2_high, c2_low]):
                continue

            # Bullish FVG check
            if c2_low > c0_high:
                gap_size = c2_low - c0_high
                gap_pct = gap_size / c0_high if c0_high > 0 else 0
                if gap_pct >= min_gap_pct:
                    # Check subsequent price action for mitigation
                    subsequent_lows = df["Low"].iloc[i + 1:] if i + 1 < n else pd.Series(dtype=float)
                    min_after = float(subsequent_lows.min()) if not subsequent_lows.empty else c2_low

                    is_mitigated = min_after <= c0_high
                    is_active = (current_price >= c0_high) and not is_mitigated
                    consequent_encroachment = round((c0_high + c2_low) / 2.0, 2)

                    bullish_fvgs.append({
                        "type": "BULLISH_FVG",
                        "top": round(c2_low, 2),
                        "bottom": round(c0_high, 2),
                        "consequent_encroachment": consequent_encroachment,
                        "gap_size": round(gap_size, 2),
                        "candle_time": c1_time,
                        "candle_index": i - 1,
                        "mitigated": is_mitigated,
                        "is_active": is_active,
                    })

            # Bearish FVG check
            elif c0_low > c2_high:
                gap_size = c0_low - c2_high
                gap_pct = gap_size / c2_high if c2_high > 0 else 0
                if gap_pct >= min_gap_pct:
                    subsequent_highs = df["High"].iloc[i + 1:] if i + 1 < n else pd.Series(dtype=float)
                    max_after = float(subsequent_highs.max()) if not subsequent_highs.empty else c2_high

                    is_mitigated = max_after >= c0_low
                    is_active = (current_price <= c0_low) and not is_mitigated
                    consequent_encroachment = round((c0_low + c2_high) / 2.0, 2)

                    bearish_fvgs.append({
                        "type": "BEARISH_FVG",
                        "top": round(c0_low, 2),
                        "bottom": round(c2_high, 2),
                        "consequent_encroachment": consequent_encroachment,
                        "gap_size": round(gap_size, 2),
                        "candle_time": c1_time,
                        "candle_index": i - 1,
                        "mitigated": is_mitigated,
                        "is_active": is_active,
                    })

        return {
            "bullish_fvgs": bullish_fvgs,
            "bearish_fvgs": bearish_fvgs,
            "status": "VALID",
        }

    @classmethod
    def detect_liquidity_sweeps(
        cls,
        df: pd.DataFrame,
        swings: Dict[str, List[Dict[str, Any]]],
        lookback_bars: int = 15,
    ) -> Dict[str, Any]:
        """
        Detects if recent candles swept prior swing highs (BSL) or swing lows (SSL).
        - Sell-Side Liquidity (SSL) Sweep: Wick penetrated below a swing low, followed by
          immediate rejection/close above that level (hunting retail stop-losses).
        - Buy-Side Liquidity (BSL) Sweep: Wick spiked above a swing high, followed by
          immediate rejection/close below that level.
        """
        validation_err = cls.validate_ohlc_dataframe(df, min_bars=5)
        if validation_err:
            return {
                "ssl_sweep": None,
                "bsl_sweep": None,
                "has_sweep": False,
                "sweep_type": "NONE",
                "status": validation_err,
            }

        sh_list = swings.get("swing_highs", [])
        sl_list = swings.get("swing_lows", [])
        n = len(df)

        ssl_sweep_detected = None
        bsl_sweep_detected = None

        # Check Sell-Side Liquidity (SSL) Sweep
        for sl in reversed(sl_list):
            sl_price = sl.get("price")
            sl_idx = sl.get("index", 0)
            if sl_price is None or not math.isfinite(sl_price) or sl_price <= 0:
                continue

            for i in range(max(sl_idx + 1, n - lookback_bars), n):
                c_low = float(df["Low"].iloc[i])
                c_close = float(df["Close"].iloc[i])
                c_high = float(df["High"].iloc[i])

                if not all(math.isfinite(x) and x > 0 for x in [c_low, c_close, c_high]):
                    continue

                if c_low < sl_price:
                    curr_close = float(df["Close"].iloc[-1])
                    if c_close >= sl_price * 0.9995 or curr_close >= sl_price:
                        sweep_depth = round(sl_price - c_low, 2)
                        ssl_sweep_detected = {
                            "type": "SELL_SIDE_LIQUIDITY_SWEEP",
                            "swept_level": round(sl_price, 2),
                            "sweep_wick_low": round(c_low, 2),
                            "low_price": round(c_low, 2),
                            "sweep_depth": sweep_depth,
                            "reclaim_price": round(c_close, 2),
                            "candle_time": str(df.index[i]),
                            "bars_ago": n - 1 - i,
                            "interpretation": f"Hunted retail sell stops below {sl_price:,.2f} with {sweep_depth:.2f} pt wick; reclaimed aggressively.",
                        }
                        break
            if ssl_sweep_detected:
                break

        # Check Buy-Side Liquidity (BSL) Sweep
        for sh in reversed(sh_list):
            sh_price = sh.get("price")
            sh_idx = sh.get("index", 0)
            if sh_price is None or not math.isfinite(sh_price) or sh_price <= 0:
                continue

            for i in range(max(sh_idx + 1, n - lookback_bars), n):
                c_high = float(df["High"].iloc[i])
                c_close = float(df["Close"].iloc[i])

                if not all(math.isfinite(x) and x > 0 for x in [c_high, c_close]):
                    continue

                if c_high > sh_price:
                    curr_close = float(df["Close"].iloc[-1])
                    if c_close <= sh_price * 1.0005 or curr_close <= sh_price:
                        sweep_depth = round(c_high - sh_price, 2)
                        bsl_sweep_detected = {
                            "type": "BUY_SIDE_LIQUIDITY_SWEEP",
                            "swept_level": round(sh_price, 2),
                            "sweep_wick_high": round(c_high, 2),
                            "high_price": round(c_high, 2),
                            "sweep_depth": sweep_depth,
                            "reclaim_price": round(c_close, 2),
                            "candle_time": str(df.index[i]),
                            "bars_ago": n - 1 - i,
                            "interpretation": f"Hunted retail buy stops above {sh_price:,.2f} with {sweep_depth:.2f} pt wick; rejected downward.",
                        }
                        break
            if bsl_sweep_detected:
                break

        sweep_type = "NONE"
        if ssl_sweep_detected and not bsl_sweep_detected:
            sweep_type = "BULLISH_SSL_SWEEP"
        elif bsl_sweep_detected and not ssl_sweep_detected:
            sweep_type = "BEARISH_BSL_SWEEP"
        elif ssl_sweep_detected and bsl_sweep_detected:
            if ssl_sweep_detected["bars_ago"] <= bsl_sweep_detected["bars_ago"]:
                sweep_type = "BULLISH_SSL_SWEEP"
            else:
                sweep_type = "BEARISH_BSL_SWEEP"

        return {
            "ssl_sweep": ssl_sweep_detected,
            "bsl_sweep": bsl_sweep_detected,
            "has_sweep": (ssl_sweep_detected is not None or bsl_sweep_detected is not None),
            "sweep_type": sweep_type,
            "status": "VALID",
        }

    @classmethod
    def detect_order_blocks(
        cls,
        df: pd.DataFrame,
        fvgs: Dict[str, List[Dict[str, Any]]],
        lookback_bars: int = 30,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detects Institutional Order Blocks:
        - Bullish Order Block (OB): The last down candle (Close < Open) before an impulsive
          expansion move that produced a Fair Value Gap or broken swing.
        - Bearish Order Block (OB): The last up candle (Close > Open) before an impulsive downward drop.
        """
        validation_err = cls.validate_ohlc_dataframe(df, min_bars=5)
        if validation_err:
            return {"bullish_obs": [], "bearish_obs": [], "status": validation_err}

        bullish_obs = []
        bearish_obs = []
        n = len(df)
        current_price = float(df["Close"].iloc[-1])

        start_idx = max(1, n - lookback_bars)

        # 1. Bullish Order Blocks
        for i in range(start_idx, n - 1):
            o_i = float(df["Open"].iloc[i])
            c_i = float(df["Close"].iloc[i])
            h_i = float(df["High"].iloc[i])
            l_i = float(df["Low"].iloc[i])

            if not all(math.isfinite(x) and x > 0 for x in [o_i, c_i, h_i, l_i]):
                continue

            # Is down candle
            if c_i <= o_i:
                next_close = float(df["Close"].iloc[min(i + 2, n - 1)])
                expansion = next_close - h_i
                if expansion > (h_i - l_i) * 0.8:
                    subsequent_lows = df["Low"].iloc[i + 1:]
                    min_after = float(subsequent_lows.min()) if not subsequent_lows.empty else l_i

                    if min_after >= l_i:
                        mean_threshold = round((h_i + l_i) / 2.0, 2)
                        is_active = (current_price >= l_i)
                        is_testing = (l_i <= current_price <= h_i * 1.002)

                        bullish_obs.append({
                            "type": "BULLISH_ORDER_BLOCK",
                            "ob_top": round(h_i, 2),
                            "ob_mean_threshold": mean_threshold,
                            "mean_threshold": mean_threshold,
                            "ob_low": round(l_i, 2),
                            "candle_time": str(df.index[i]),
                            "candle_index": i,
                            "is_active": is_active,
                            "is_testing": is_testing,
                            "is_mitigated": not is_active,
                        })

        # 2. Bearish Order Blocks
        for i in range(start_idx, n - 1):
            o_i = float(df["Open"].iloc[i])
            c_i = float(df["Close"].iloc[i])
            h_i = float(df["High"].iloc[i])
            l_i = float(df["Low"].iloc[i])

            if not all(math.isfinite(x) and x > 0 for x in [o_i, c_i, h_i, l_i]):
                continue

            if c_i >= o_i:
                next_close = float(df["Close"].iloc[min(i + 2, n - 1)])
                displacement = l_i - next_close
                if displacement > (h_i - l_i) * 0.8:
                    subsequent_highs = df["High"].iloc[i + 1:]
                    max_after = float(subsequent_highs.max()) if not subsequent_highs.empty else h_i

                    if max_after <= h_i:
                        mean_threshold = round((h_i + l_i) / 2.0, 2)
                        is_active = (current_price <= h_i)
                        is_testing = (l_i * 0.998 <= current_price <= h_i)

                        bearish_obs.append({
                            "type": "BEARISH_ORDER_BLOCK",
                            "ob_top": round(h_i, 2),
                            "ob_mean_threshold": mean_threshold,
                            "mean_threshold": mean_threshold,
                            "ob_low": round(l_i, 2),
                            "candle_time": str(df.index[i]),
                            "candle_index": i,
                            "is_active": is_active,
                            "is_testing": is_testing,
                            "is_mitigated": not is_active,
                        })

        return {
            "bullish_obs": bullish_obs,
            "bearish_obs": bearish_obs,
            "status": "VALID",
        }

    @classmethod
    def detect_bos_and_choch(cls, df: pd.DataFrame, swings: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Detects Break of Structure (BOS) and Change of Character (CHoCH):
        - Bullish BOS: Price breaks & closes above the previous swing high in an established uptrend.
        - Bearish BOS: Price breaks & closes below the previous swing low in an established downtrend.
        - Bullish CHoCH: In a prevailing downtrend, price takes out the last Lower High, signaling structural reversal to Bullish.
        - Bearish CHoCH: In a prevailing uptrend, price takes out the last Higher Low, signaling structural reversal to Bearish.
        Crucial: A BOS or CHoCH must NOT show CONFIRMED unless required price levels and confirmation conditions are valid.
        """
        validation_err = cls.validate_ohlc_dataframe(df, min_bars=10)
        if validation_err:
            desc = "INSUFFICIENT HISTORICAL DATA" if validation_err == "INSUFFICIENT HISTORICAL DATA" else "UNAVAILABLE — INVALID INPUT DATA"
            return {
                "bos": {"detected": False, "confirmed": False, "type": "NONE", "level": 0.0, "broken_level": 0.0, "time": "--", "description": desc},
                "choch": {"detected": False, "confirmed": False, "type": "NONE", "level": 0.0, "broken_level": 0.0, "time": "--", "description": desc},
                "structure_state": "NEUTRAL_CONSOLIDATION",
                "status": validation_err,
            }

        sh_list = swings.get("swing_highs", [])
        sl_list = swings.get("swing_lows", [])
        if len(sh_list) < 2 or len(sl_list) < 2:
            return {
                "bos": {"detected": False, "confirmed": False, "type": "NONE", "level": 0.0, "broken_level": 0.0, "time": "--", "description": "INSUFFICIENT HISTORICAL DATA"},
                "choch": {"detected": False, "confirmed": False, "type": "NONE", "level": 0.0, "broken_level": 0.0, "time": "--", "description": "INSUFFICIENT HISTORICAL DATA"},
                "structure_state": "SIDEWAYS_RANGE",
                "status": "INSUFFICIENT HISTORICAL DATA",
            }

        current_close = float(df["Close"].iloc[-1])
        prev_sh, last_sh = sh_list[-2].get("price"), sh_list[-1].get("price")
        prev_sl, last_sl = sl_list[-2].get("price"), sl_list[-1].get("price")

        # Validate that all required price levels are valid finite numbers
        if not all(isinstance(p, (int, float)) and math.isfinite(p) and p > 0 for p in [current_close, prev_sh, last_sh, prev_sl, last_sl]):
            return {
                "bos": {"detected": False, "confirmed": False, "type": "NONE", "level": 0.0, "broken_level": 0.0, "time": "--", "description": "UNAVAILABLE — INVALID INPUT DATA"},
                "choch": {"detected": False, "confirmed": False, "type": "NONE", "level": 0.0, "broken_level": 0.0, "time": "--", "description": "UNAVAILABLE — INVALID INPUT DATA"},
                "structure_state": "NEUTRAL_CONSOLIDATION",
                "status": "UNAVAILABLE — INVALID INPUT DATA",
            }

        is_prev_uptrend = (last_sh > prev_sh) and (last_sl > prev_sl)
        is_prev_downtrend = (last_sh < prev_sh) and (last_sl < prev_sl)

        time_str = str(df.index[-1]) if len(df.index) > 0 else "--"
        bos_info = {"detected": False, "confirmed": False, "type": "NONE", "level": 0.0, "broken_level": 0.0, "time": time_str, "description": "No active break of structure."}
        choch_info = {"detected": False, "confirmed": False, "type": "NONE", "level": 0.0, "broken_level": 0.0, "time": time_str, "description": "No change of character."}

        # 1. BOS (Break of Structure - Trend Continuation)
        if is_prev_uptrend and current_close > last_sh:
            bos_info = {
                "detected": True,
                "confirmed": True,
                "type": "BULLISH_BOS",
                "level": round(last_sh, 2),
                "broken_level": round(last_sh, 2),
                "break_candle_price": round(current_close, 2),
                "trend": "BULLISH",
                "time": time_str,
                "description": f"Bullish BOS confirmed: 5m candle closed above previous swing high at {last_sh:,.2f}."
            }
        elif is_prev_downtrend and current_close < last_sl:
            bos_info = {
                "detected": True,
                "confirmed": True,
                "type": "BEARISH_BOS",
                "level": round(last_sl, 2),
                "broken_level": round(last_sl, 2),
                "break_candle_price": round(current_close, 2),
                "trend": "BEARISH",
                "time": time_str,
                "description": f"Bearish BOS confirmed: 5m candle closed below previous swing low at {last_sl:,.2f}."
            }

        # 2. CHoCH (Change of Character - Reversal)
        if is_prev_downtrend and current_close > last_sh:
            choch_info = {
                "detected": True,
                "confirmed": True,
                "type": "BULLISH_CHOCH",
                "level": round(last_sh, 2),
                "broken_level": round(last_sh, 2),
                "break_candle_price": round(current_close, 2),
                "state": "Shift Confirmed",
                "time": time_str,
                "description": f"Bullish CHoCH reversal: Broken previous lower high at {last_sh:,.2f}; supply flipped to demand."
            }
        elif is_prev_uptrend and current_close < last_sl:
            choch_info = {
                "detected": True,
                "confirmed": True,
                "type": "BEARISH_CHOCH",
                "level": round(last_sl, 2),
                "broken_level": round(last_sl, 2),
                "break_candle_price": round(current_close, 2),
                "state": "Shift Confirmed",
                "time": time_str,
                "description": f"Bearish CHoCH reversal: Broken previous higher low at {last_sl:,.2f}; demand flipped to supply."
            }

        return {
            "bos": bos_info,
            "choch": choch_info,
            "structure_state": "BULLISH_EXPANSION" if is_prev_uptrend else ("BEARISH_EXPANSION" if is_prev_downtrend else "CONSOLIDATION"),
            "status": "VALID",
        }

    @classmethod
    def analyze_smc(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Executes end-to-end Smart Money Concepts analysis:
        - Validates OHLC integrity first.
        - Detects Swings, Liquidity Sweeps, FVGs, Order Blocks.
        - Identifies high-conviction Institutional Setups.
        - Computes FIXED Structural Price Anchors (Entry, Invalidation SL, Targets).
        - Rejects incomplete data without inventing replacement price levels or signals.
        """
        validation_err = cls.validate_ohlc_dataframe(df, min_bars=10)
        if validation_err:
            desc = "INSUFFICIENT HISTORICAL DATA" if validation_err == "INSUFFICIENT HISTORICAL DATA" else "UNAVAILABLE — INVALID INPUT DATA"
            return {
                "status": validation_err,
                "has_smc_setup": False,
                "setup_type": validation_err,
                "fixed_entry_price": 0.0,
                "fixed_stop_loss": 0.0,
                "fixed_target_1": 0.0,
                "fixed_target_2": 0.0,
                "risk_reward_ratio": "N/A",
                "details_why_it_works": [desc],
                "reversal_risk": {
                    "chance_pct": 0.0,
                    "risk_level": "UNKNOWN",
                    "threats": [desc],
                    "invalidation_trigger": desc,
                },
                "active_bullish_ob": None,
                "active_bearish_ob": None,
                "active_bullish_fvg": None,
                "active_bearish_fvg": None,
                "liquidity_sweep": None,
                "smc_matrix": {
                    "bos": None,
                    "choch": None,
                    "structure_state": desc,
                    "liquidity_sweep": None,
                    "ssl_sweep": None,
                    "bsl_sweep": None,
                    "active_bullish_ob": None,
                    "active_bearish_ob": None,
                    "active_bullish_fvg": None,
                    "active_bearish_fvg": None,
                    "bullish_obs_count": 0,
                    "bearish_obs_count": 0,
                    "bullish_fvgs_count": 0,
                    "bearish_fvgs_count": 0,
                },
            }

        try:
            current_price = float(df["Close"].iloc[-1])
            if not math.isfinite(current_price) or current_price <= 0:
                raise ValueError("Invalid current_price")

            swings = MarketStructureAnalyzer.find_swings(df, window=2)
            fvgs = cls.detect_fair_value_gaps(df)
            sweeps = cls.detect_liquidity_sweeps(df, swings, lookback_bars=20)
            obs = cls.detect_order_blocks(df, fvgs, lookback_bars=30)
            bos_choch = cls.detect_bos_and_choch(df, swings)

            bull_obs = [ob for ob in obs["bullish_obs"] if ob["is_active"]]
            bear_obs = [ob for ob in obs["bearish_obs"] if ob["is_active"]]

            bull_fvgs = [f for f in fvgs["bullish_fvgs"] if f["is_active"]]
            bear_fvgs = [f for f in fvgs["bearish_fvgs"] if f["is_active"]]

            recent_ssl_sweep = sweeps.get("ssl_sweep")
            recent_bsl_sweep = sweeps.get("bsl_sweep")

            nearest_bull_ob = None
            for ob in reversed(bull_obs):
                if ob["ob_top"] <= current_price * 1.008:
                    nearest_bull_ob = ob
                    break
            if not nearest_bull_ob and bull_obs:
                nearest_bull_ob = bull_obs[-1]

            nearest_bull_fvg = None
            for f in reversed(bull_fvgs):
                if f["top"] <= current_price * 1.008:
                    nearest_bull_fvg = f
                    break
            if not nearest_bull_fvg and bull_fvgs:
                nearest_bull_fvg = bull_fvgs[-1]

            nearest_bear_fvg = None
            for f in reversed(bear_fvgs):
                if f["bottom"] >= current_price * 0.995:
                    nearest_bear_fvg = f
                    break

            nearest_bear_ob = bear_obs[-1] if bear_obs else None

            sh_list = swings.get("swing_highs", [])
            sl_list = swings.get("swing_lows", [])
            overhead_sh = [s["price"] for s in sh_list if s["price"] > current_price and math.isfinite(s["price"])]
            nearest_target_sh = min(overhead_sh) if overhead_sh else float(df["High"].tail(20).max())

            details_why: List[str] = []
            threats: List[str] = []
            chance_reversal = 20.0
            risk_level = "LOW"

            has_smc_setup = False
            fixed_entry = 0.0
            fixed_sl = 0.0
            fixed_t1 = 0.0
            fixed_t2 = 0.0
            rr_str = "N/A"

            # Case A: Confluent Bullish Liquidity Sweep + Order Block / FVG
            if recent_ssl_sweep and (nearest_bull_ob or nearest_bull_fvg):
                setup_type = "BULLISH_LIQUIDITY_SWEEP_PLUS_ORDER_BLOCK"
                has_smc_setup = True

                if nearest_bull_ob:
                    fixed_entry = nearest_bull_ob["ob_mean_threshold"]
                    ob_desc = f"Institutional Bullish Order Block at {nearest_bull_ob['ob_low']:,.2f} - {nearest_bull_ob['ob_top']:,.2f} (50% MT: {fixed_entry:,.2f})"
                    sl_base = min(nearest_bull_ob["ob_low"], recent_ssl_sweep["sweep_wick_low"])
                else:
                    fixed_entry = nearest_bull_fvg["consequent_encroachment"]
                    ob_desc = f"Bullish Fair Value Gap (FVG) Consequent Encroachment at {fixed_entry:,.2f}"
                    sl_base = recent_ssl_sweep["sweep_wick_low"]

                fixed_sl = round(sl_base * 0.9985, 2)
                risk_dist = max(fixed_entry - fixed_sl, current_price * 0.003)
                fixed_t1 = round(max(nearest_target_sh, fixed_entry + (risk_dist * 1.6)), 2)
                fixed_t2 = round(fixed_entry + (risk_dist * 2.6), 2)
                rr_str = f"1:{(fixed_t1 - fixed_entry) / risk_dist:.1f}"

                details_why.append(
                    f"LIQUIDITY PURGE: Smart money swept Sell-Side Liquidity (SSL) below prior low {recent_ssl_sweep['swept_level']:,.2f} "
                    f"with a {recent_ssl_sweep['sweep_depth']:.2f} pt probe, triggering retail panic stops."
                )
                details_why.append(
                    f"ORDER BLOCK ACCUMULATION: Price is anchored to {ob_desc}, where institutional unfilled buy orders reside."
                )
                if nearest_bull_fvg:
                    details_why.append(
                        f"FVG IMBALANCE: Unfilled Fair Value Gap between {nearest_bull_fvg['bottom']:,.2f} - {nearest_bull_fvg['top']:,.2f} creates an institutional vacuum attracting price upward."
                    )
                details_why.append(
                    f"TRAPPED LIQUIDITY TARGET: Retail breakout sellers trapped under the sweep now provide fuel for the rally towards Buy-Side Liquidity at {fixed_t1:,.2f}."
                )

            # Case B: Clean Bullish Order Block / FVG Retest (No recent sweep)
            elif nearest_bull_ob or nearest_bull_fvg:
                setup_type = "BULLISH_ORDER_BLOCK_FVG_RETEST"
                has_smc_setup = True

                if nearest_bull_ob:
                    fixed_entry = nearest_bull_ob["ob_mean_threshold"]
                    fixed_sl = round(nearest_bull_ob["ob_low"] * 0.9985, 2)
                    details_why.append(
                        f"UNMITIGATED ORDER BLOCK: Institutional accumulation block at {nearest_bull_ob['ob_low']:,.2f} - {nearest_bull_ob['ob_top']:,.2f}. Institutions defend the 50% Mean Threshold ({fixed_entry:,.2f})."
                    )
                else:
                    fixed_entry = nearest_bull_fvg["consequent_encroachment"]
                    fixed_sl = round(nearest_bull_fvg["bottom"] * 0.9985, 2)
                    details_why.append(
                        f"FAIR VALUE GAP (FVG): Imbalance retest at {fixed_entry:,.2f}. Smart money algorithmic price delivery seeks to rebalance this vacuum before continuing the expansion."
                    )

                risk_dist = max(fixed_entry - fixed_sl, current_price * 0.003)
                fixed_t1 = round(max(nearest_target_sh, fixed_entry + (risk_dist * 1.5)), 2)
                fixed_t2 = round(fixed_entry + (risk_dist * 2.5), 2)
                rr_str = f"1:{(fixed_t1 - fixed_entry) / risk_dist:.1f}"

            # Case C: Baseline Structural Pullback only if verified swings exist
            elif sl_list and len(sl_list) >= 1:
                setup_type = "STRUCTURAL_SWING_PULLBACK"
                recent_sl = sl_list[-1]["price"]
                if math.isfinite(recent_sl) and recent_sl > 0:
                    has_smc_setup = True
                    fixed_entry = round(recent_sl * 1.0015, 2)
                    fixed_sl = round(recent_sl * 0.9975, 2)
                    risk_dist = max(fixed_entry - fixed_sl, current_price * 0.003)
                    fixed_t1 = round(nearest_target_sh, 2)
                    fixed_t2 = round(fixed_entry + (risk_dist * 2.2), 2)
                    rr_str = "1:2.0"
                    details_why.append(
                        f"STRUCTURAL HIGHER-LOW: Price is forming a higher swing low above {recent_sl:,.2f}, confirming preservation of bullish market structure."
                    )
                else:
                    setup_type = "NO_SMC_SETUP"
                    details_why.append("Awaiting structural swing confirmation.")
            else:
                setup_type = "NO_SMC_SETUP"
                details_why.append("Awaiting clear institutional order blocks or liquidity sweeps.")

            # Reversal Threats
            if nearest_bear_fvg and nearest_bear_fvg["bottom"] < fixed_t1:
                chance_reversal += 15.0
                threats.append(
                    f"Opposing Bearish FVG exists overhead at {nearest_bear_fvg['bottom']:,.2f} - {nearest_bear_fvg['top']:,.2f}, which may act as an institutional supply barrier."
                )

            if nearest_bear_ob and nearest_bear_ob["ob_low"] < fixed_t1:
                chance_reversal += 15.0
                threats.append(
                    f"Overhead Bearish Order Block at {nearest_bear_ob['ob_low']:,.2f} - {nearest_bear_ob['ob_top']:,.2f} could trigger secondary selling pressure."
                )

            if recent_bsl_sweep and recent_bsl_sweep.get("bars_ago", 999) <= 8:
                chance_reversal += 20.0
                threats.append(
                    f"Recent Buy-Side Liquidity (BSL) sweep at {recent_bsl_sweep['swept_level']:,.2f} was rejected, indicating smart money took profit at the highs."
                )

            if not threats:
                threats.append("No immediate opposing Bearish FVG or Order Block detected below Target 1. Clear runway to target.")

            chance_reversal = min(max(chance_reversal, 15.0), 80.0)
            if chance_reversal < 30.0:
                risk_level = "LOW"
            elif chance_reversal <= 50.0:
                risk_level = "MODERATE"
            else:
                risk_level = "HIGH"

            invalidation_trigger = f"5-minute candle body CLOSE below Invalidation Stop-Loss at {fixed_sl:,.2f} permanently cancels this SMC setup." if fixed_sl > 0 else "Wait for defined structural levels."

            smc_matrix = {
                "bos": bos_choch.get("bos"),
                "choch": bos_choch.get("choch"),
                "structure_state": bos_choch.get("structure_state"),
                "liquidity_sweep": recent_ssl_sweep or recent_bsl_sweep,
                "ssl_sweep": recent_ssl_sweep,
                "bsl_sweep": recent_bsl_sweep,
                "active_bullish_ob": nearest_bull_ob,
                "active_bearish_ob": nearest_bear_ob,
                "active_bullish_fvg": nearest_bull_fvg,
                "active_bearish_fvg": nearest_bear_fvg,
                "bullish_obs_count": len(bull_obs),
                "bearish_obs_count": len(bear_obs),
                "bullish_fvgs_count": len(bull_fvgs),
                "bearish_fvgs_count": len(bear_fvgs),
            }

            return {
                "status": "VALID",
                "has_smc_setup": has_smc_setup,
                "setup_type": setup_type,
                "fixed_entry_price": fixed_entry if math.isfinite(fixed_entry) else 0.0,
                "fixed_stop_loss": fixed_sl if math.isfinite(fixed_sl) else 0.0,
                "fixed_target_1": fixed_t1 if math.isfinite(fixed_t1) else 0.0,
                "fixed_target_2": fixed_t2 if math.isfinite(fixed_t2) else 0.0,
                "risk_reward_ratio": rr_str,
                "details_why_it_works": details_why,
                "reversal_risk": {
                    "chance_pct": round(chance_reversal, 1),
                    "risk_level": risk_level,
                    "threats": threats,
                    "invalidation_trigger": invalidation_trigger,
                },
                "active_bullish_ob": nearest_bull_ob,
                "active_bearish_ob": nearest_bear_ob,
                "active_bullish_fvg": nearest_bull_fvg,
                "active_bearish_fvg": nearest_bear_fvg,
                "liquidity_sweep": recent_ssl_sweep or recent_bsl_sweep,
                "smc_matrix": smc_matrix,
            }
        except Exception as e:
            logger.error(f"Error executing SMC analysis: {e}")
            return {
                "status": "UNAVAILABLE — INVALID INPUT DATA",
                "has_smc_setup": False,
                "setup_type": "UNAVAILABLE — INVALID INPUT DATA",
                "fixed_entry_price": 0.0,
                "fixed_stop_loss": 0.0,
                "fixed_target_1": 0.0,
                "fixed_target_2": 0.0,
                "risk_reward_ratio": "N/A",
                "details_why_it_works": ["UNAVAILABLE — INVALID INPUT DATA"],
                "reversal_risk": {
                    "chance_pct": 0.0,
                    "risk_level": "UNKNOWN",
                    "threats": ["Calculation failed due to invalid data."],
                    "invalidation_trigger": "UNAVAILABLE — INVALID INPUT DATA",
                },
                "active_bullish_ob": None,
                "active_bearish_ob": None,
                "active_bullish_fvg": None,
                "active_bearish_fvg": None,
                "liquidity_sweep": None,
                "smc_matrix": {
                    "bos": None,
                    "choch": None,
                    "structure_state": "UNAVAILABLE — INVALID INPUT DATA",
                    "liquidity_sweep": None,
                    "ssl_sweep": None,
                    "bsl_sweep": None,
                    "active_bullish_ob": None,
                    "active_bearish_ob": None,
                    "active_bullish_fvg": None,
                    "active_bearish_fvg": None,
                    "bullish_obs_count": 0,
                    "bearish_obs_count": 0,
                    "bullish_fvgs_count": 0,
                    "bearish_fvgs_count": 0,
                },
            }
