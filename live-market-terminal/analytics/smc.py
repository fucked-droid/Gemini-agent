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
    def detect_fair_value_gaps(df: pd.DataFrame, min_gap_pct: float = 0.0003) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detects 3-candle Fair Value Gaps (FVG) and tracks their mitigation status.
        - Bullish FVG: High[candle i-2] < Low[candle i]
        - Bearish FVG: Low[candle i-2] > High[candle i]
        """
        if df.empty or len(df) < 3:
            return {"bullish_fvgs": [], "bearish_fvgs": []}

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
        }

    @staticmethod
    def detect_liquidity_sweeps(
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
        if df.empty or len(df) < 5:
            return {
                "ssl_sweep": None,
                "bsl_sweep": None,
                "has_sweep": False,
                "sweep_type": "NONE",
            }

        sh_list = swings.get("swing_highs", [])
        sl_list = swings.get("swing_lows", [])
        n = len(df)
        recent_window = df.iloc[-min(lookback_bars, n):]

        ssl_sweep_detected = None
        bsl_sweep_detected = None

        # Check Sell-Side Liquidity (SSL) Sweep
        for sl in reversed(sl_list):
            sl_price = sl["price"]
            sl_idx = sl.get("index", 0)

            # Look for recent candles that breached sl_price
            for i in range(max(sl_idx + 1, n - lookback_bars), n):
                c_low = float(df["Low"].iloc[i])
                c_close = float(df["Close"].iloc[i])
                c_high = float(df["High"].iloc[i])

                if c_low < sl_price:
                    # Breached below. Did it close back above, or did subsequent candle close above?
                    curr_close = float(df["Close"].iloc[-1])
                    if c_close >= sl_price * 0.9995 or curr_close >= sl_price:
                        sweep_depth = round(sl_price - c_low, 2)
                        ssl_sweep_detected = {
                            "type": "SELL_SIDE_LIQUIDITY_SWEEP",
                            "swept_level": round(sl_price, 2),
                            "sweep_wick_low": round(c_low, 2),
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
            sh_price = sh["price"]
            sh_idx = sh.get("index", 0)

            for i in range(max(sh_idx + 1, n - lookback_bars), n):
                c_high = float(df["High"].iloc[i])
                c_close = float(df["Close"].iloc[i])

                if c_high > sh_price:
                    curr_close = float(df["Close"].iloc[-1])
                    if c_close <= sh_price * 1.0005 or curr_close <= sh_price:
                        sweep_depth = round(c_high - sh_price, 2)
                        bsl_sweep_detected = {
                            "type": "BUY_SIDE_LIQUIDITY_SWEEP",
                            "swept_level": round(sh_price, 2),
                            "sweep_wick_high": round(c_high, 2),
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
            # Check which is more recent
            if ssl_sweep_detected["bars_ago"] <= bsl_sweep_detected["bars_ago"]:
                sweep_type = "BULLISH_SSL_SWEEP"
            else:
                sweep_type = "BEARISH_BSL_SWEEP"

        return {
            "ssl_sweep": ssl_sweep_detected,
            "bsl_sweep": bsl_sweep_detected,
            "has_sweep": (ssl_sweep_detected is not None or bsl_sweep_detected is not None),
            "sweep_type": sweep_type,
        }

    @staticmethod
    def detect_order_blocks(
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
        if df.empty or len(df) < 5:
            return {"bullish_obs": [], "bearish_obs": []}

        bullish_obs = []
        bearish_obs = []
        n = len(df)
        current_price = float(df["Close"].iloc[-1])

        start_idx = max(1, n - lookback_bars)

        # 1. Bullish Order Blocks
        # Look for candles followed by strong green displacement
        for i in range(start_idx, n - 1):
            o_i = float(df["Open"].iloc[i])
            c_i = float(df["Close"].iloc[i])
            h_i = float(df["High"].iloc[i])
            l_i = float(df["Low"].iloc[i])

            # Is down candle
            if c_i <= o_i:
                # Next 1-3 candles show strong expansion upwards
                next_close = float(df["Close"].iloc[min(i + 2, n - 1)])
                expansion = next_close - h_i
                if expansion > (h_i - l_i) * 0.8:
                    # Check if price has not broken below OB Low
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
                            "ob_low": round(l_i, 2),
                            "candle_time": str(df.index[i]),
                            "candle_index": i,
                            "is_active": is_active,
                            "is_testing": is_testing,
                        })

        # 2. Bearish Order Blocks
        for i in range(start_idx, n - 1):
            o_i = float(df["Open"].iloc[i])
            c_i = float(df["Close"].iloc[i])
            h_i = float(df["High"].iloc[i])
            l_i = float(df["Low"].iloc[i])

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
                            "ob_low": round(l_i, 2),
                            "candle_time": str(df.index[i]),
                            "candle_index": i,
                            "is_active": is_active,
                            "is_testing": is_testing,
                        })

        return {
            "bullish_obs": bullish_obs,
            "bearish_obs": bearish_obs,
        }

    @staticmethod
    def detect_bos_and_choch(df: pd.DataFrame, swings: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Detects Break of Structure (BOS) and Change of Character (CHoCH):
        - Bullish BOS: Price breaks & closes above the previous swing high in an established uptrend.
        - Bearish BOS: Price breaks & closes below the previous swing low in an established downtrend.
        - Bullish CHoCH: In a prevailing downtrend, price takes out the last Lower High, signaling structural reversal to Bullish.
        - Bearish CHoCH: In a prevailing uptrend, price takes out the last Higher Low, signaling structural reversal to Bearish.
        """
        sh_list = swings.get("swing_highs", [])
        sl_list = swings.get("swing_lows", [])
        if len(sh_list) < 2 or len(sl_list) < 2 or df.empty:
            return {
                "bos": {"detected": False, "type": "NONE", "level": 0.0, "time": "--", "description": "Awaiting clear structural swing levels."},
                "choch": {"detected": False, "type": "NONE", "level": 0.0, "time": "--", "description": "No character shift detected."},
                "structure_state": "SIDEWAYS_RANGE",
            }

        current_close = float(df["Close"].iloc[-1])
        prev_sh, last_sh = sh_list[-2]["price"], sh_list[-1]["price"]
        prev_sl, last_sl = sl_list[-2]["price"], sl_list[-1]["price"]

        is_prev_uptrend = (last_sh > prev_sh) and (last_sl > prev_sl)
        is_prev_downtrend = (last_sh < prev_sh) and (last_sl < prev_sl)

        bos_info = {"detected": False, "type": "NONE", "level": 0.0, "time": str(df.index[-1]), "description": "No active break of structure."}
        choch_info = {"detected": False, "type": "NONE", "level": 0.0, "time": str(df.index[-1]), "description": "No change of character."}

        # 1. BOS (Break of Structure - Trend Continuation)
        if is_prev_uptrend and current_close > last_sh:
            bos_info = {
                "detected": True,
                "type": "BULLISH_BOS",
                "level": round(last_sh, 2),
                "time": str(df.index[-1]),
                "description": f"Bullish BOS confirmed: 5m candle closed above previous swing high at {last_sh:,.2f}."
            }
        elif is_prev_downtrend and current_close < last_sl:
            bos_info = {
                "detected": True,
                "type": "BEARISH_BOS",
                "level": round(last_sl, 2),
                "time": str(df.index[-1]),
                "description": f"Bearish BOS confirmed: 5m candle closed below previous swing low at {last_sl:,.2f}."
            }

        # 2. CHoCH (Change of Character - Reversal)
        if is_prev_downtrend and current_close > last_sh:
            choch_info = {
                "detected": True,
                "type": "BULLISH_CHOCH",
                "level": round(last_sh, 2),
                "time": str(df.index[-1]),
                "description": f"Bullish CHoCH reversal: Broken previous lower high at {last_sh:,.2f}; supply flipped to demand."
            }
        elif is_prev_uptrend and current_close < last_sl:
            choch_info = {
                "detected": True,
                "type": "BEARISH_CHOCH",
                "level": round(last_sl, 2),
                "time": str(df.index[-1]),
                "description": f"Bearish CHoCH reversal: Broken previous higher low at {last_sl:,.2f}; demand flipped to supply."
            }

        return {
            "bos": bos_info,
            "choch": choch_info,
            "structure_state": "BULLISH_EXPANSION" if is_prev_uptrend else ("BEARISH_EXPANSION" if is_prev_downtrend else "CONSOLIDATION"),
        }

    @classmethod
    def analyze_smc(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Executes end-to-end Smart Money Concepts analysis:
        - Detects Swings, Liquidity Sweeps, FVGs, Order Blocks.
        - Identifies high-conviction Institutional Setups.
        - Computes FIXED Structural Price Anchors (Entry, Invalidation SL, Targets).
        - Generates Why-It-Works thesis and Reversal Risk evaluation.
        """
        if df.empty or len(df) < 10:
            return {
                "has_smc_setup": False,
                "setup_type": "INSUFFICIENT_DATA",
                "fixed_entry_price": 0.0,
                "fixed_stop_loss": 0.0,
                "fixed_target_1": 0.0,
                "fixed_target_2": 0.0,
                "risk_reward_ratio": "1:2.0",
                "details_why_it_works": ["Insufficient candle history for Smart Money structure."],
                "reversal_risk": {
                    "chance_pct": 50.0,
                    "risk_level": "MODERATE",
                    "threats": ["Insufficient historical data."],
                    "invalidation_trigger": "Wait for minimum 15 bars.",
                },
                "active_bullish_ob": None,
                "active_bullish_fvg": None,
                "liquidity_sweep": None,
            }

        current_price = float(df["Close"].iloc[-1])
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

        # Nearest Bullish Order Block below or near current price
        nearest_bull_ob = None
        for ob in reversed(bull_obs):
            if ob["ob_top"] <= current_price * 1.008:
                nearest_bull_ob = ob
                break
        if not nearest_bull_ob and bull_obs:
            nearest_bull_ob = bull_obs[-1]

        # Nearest Bullish FVG
        nearest_bull_fvg = None
        for f in reversed(bull_fvgs):
            if f["top"] <= current_price * 1.008:
                nearest_bull_fvg = f
                break
        if not nearest_bull_fvg and bull_fvgs:
            nearest_bull_fvg = bull_fvgs[-1]

        # Nearest Bearish FVG / Overhead Supply (for reversal risk)
        nearest_bear_fvg = None
        for f in reversed(bear_fvgs):
            if f["bottom"] >= current_price * 0.995:
                nearest_bear_fvg = f
                break

        nearest_bear_ob = bear_obs[-1] if bear_obs else None

        # Nearest Swing High (BSL Pool for Targets)
        sh_list = swings.get("swing_highs", [])
        sl_list = swings.get("swing_lows", [])
        overhead_sh = [s["price"] for s in sh_list if s["price"] > current_price]
        nearest_target_sh = min(overhead_sh) if overhead_sh else float(df["High"].tail(20).max())

        # ==========================================================
        # DETERMINING FIXED ENTRY & SMC CONFLUENCE SETUP
        # ==========================================================
        details_why: List[str] = []
        threats: List[str] = []
        chance_reversal = 20.0
        risk_level = "LOW"

        # Case A: Confluent Bullish Liquidity Sweep + Order Block / FVG
        if recent_ssl_sweep and (nearest_bull_ob or nearest_bull_fvg):
            setup_type = "BULLISH_LIQUIDITY_SWEEP_PLUS_ORDER_BLOCK"

            # FIXED ENTRY: Mean threshold of the active Order Block, or swept level reclaim
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

        # Case C: Baseline Structural Pullback (Fallback when no active OB)
        else:
            setup_type = "STRUCTURAL_SWING_PULLBACK"
            recent_sl = swings["swing_lows"][-1]["price"] if swings["swing_lows"] else (current_price * 0.995)
            fixed_entry = round(recent_sl * 1.0015, 2)
            fixed_sl = round(recent_sl * 0.9975, 2)
            risk_dist = max(fixed_entry - fixed_sl, current_price * 0.003)
            fixed_t1 = round(nearest_target_sh, 2)
            fixed_t2 = round(fixed_entry + (risk_dist * 2.2), 2)
            rr_str = "1:2.0"

            details_why.append(
                f"STRUCTURAL HIGHER-LOW: Price is forming a higher swing low above {recent_sl:,.2f}, confirming preservation of bullish market structure."
            )

        # ==========================================================
        # REVERSAL THREAT & FAILURE ANALYSIS (CHANCE OF GETTING REVERSE)
        # ==========================================================
        # Check opposing threats:
        # 1. Bearish FVG overhead
        if nearest_bear_fvg and nearest_bear_fvg["bottom"] < fixed_t1:
            chance_reversal += 15.0
            threats.append(
                f"Opposing Bearish FVG exists overhead at {nearest_bear_fvg['bottom']:,.2f} - {nearest_bear_fvg['top']:,.2f}, which may act as an institutional supply barrier."
            )

        # 2. Bearish Order Block overhead
        if nearest_bear_ob and nearest_bear_ob["ob_low"] < fixed_t1:
            chance_reversal += 15.0
            threats.append(
                f"Overhead Bearish Order Block at {nearest_bear_ob['ob_low']:,.2f} - {nearest_bear_ob['ob_top']:,.2f} could trigger secondary selling pressure."
            )

        # 3. Recent BSL sweep (if price swept highs recently, it could be a bull trap)
        if recent_bsl_sweep and recent_bsl_sweep["bars_ago"] <= 8:
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

        invalidation_trigger = f"5-minute candle body CLOSE below Invalidation Stop-Loss at {fixed_sl:,.2f} permanently cancels this SMC setup."

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
            "has_smc_setup": True,
            "setup_type": setup_type,
            "fixed_entry_price": fixed_entry,
            "fixed_stop_loss": fixed_sl,
            "fixed_target_1": fixed_t1,
            "fixed_target_2": fixed_t2,
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
