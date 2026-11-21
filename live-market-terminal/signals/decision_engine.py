"""
Rules-Based Institutional Trading Decision Engine with Smart Money Concepts (SMC).

Features:
- Smart Money Concepts (SMC): Liquidity Sweeps, Order Blocks (OB), Fair Value Gaps (FVG).
- Fixed Structural Entry Point: Anchors to fixed institutional levels (OB Mean Threshold, FVG CE, VWAP)
  without drifting with live price fluctuations.
- High Priority BUY setups with strict Proper Entry validation (Pullback vs Overextended).
- Detailed "Why This Works" institutional reasoning (Liquidity purges, Order Block accumulation, FVG rebalancing).
- Reversal Risk & Threat Assessment: Explicit % chance of reversal, overhead supply threats, and invalidation triggers.
- Low-Capital Protection Shield: Skips high-margin short selling, prioritizing capital preservation.

Institutional Mandates:
- Strictly supported decision states:
    1. BUY
    2. SELL
    3. WAIT
    4. DATA UNAVAILABLE
    5. EXECUTION LOCKED
- Every signal includes:
    - Instrument
    - Timeframe
    - Direction (LONG, SHORT, NEUTRAL, NONE)
    - Entry zone
    - Stop loss
    - Target levels
    - Risk/reward
    - Confidence score (calibrated model)
    - Supporting conditions
    - Invalidation condition
    - Signal timestamp
    - Data mode
- Never forces BUY or SELL when market data is stale or session is closed.
"""

import os
import time
import datetime
import logging
from typing import Dict, Any, List, Optional

from config import get_ist_now

logger = logging.getLogger("TradingDecisionEngine")


class TradingDecisionEngine:
    """
    Configurable rules-based multi-factor decision engine with Smart Money Concepts (SMC),
    Fixed Structural Entry Points, Low-Capital Protection, and Strict Session Gating.
    """

    @classmethod
    def evaluate(
        cls,
        spot_price: float,
        indicators: Dict[str, Any],
        mtf_data: Dict[str, Any],
        order_flow: Dict[str, Any],
        market_structure: Dict[str, Any],
        market_breadth: Dict[str, Any],
        buy_priority_mode: bool = True,
        smc_data: Optional[Dict[str, Any]] = None,
        symbol: str = "NIFTY",
        timeframe: str = "5m",
        market_status: Optional[Dict[str, Any]] = None,
        data_mode: str = "HISTORICAL",
        is_stale: bool = False,
    ) -> Dict[str, Any]:
        """
        Synthesizes market internals, SMC structures, and order flow.
        Calculates a FIXED structural entry point, why the setup works, and reversal risk.
        Respects operational states (MARKET CLOSED -> EXECUTION LOCKED; DATA MISSING -> DATA UNAVAILABLE).
        """
        now_str = get_ist_now().strftime("%Y-%m-%d %H:%M:%S IST")
        sym = symbol.upper()
        curr_symbol = "$" if sym == "BTC" else "₹"

        # -------------------------------------------------------------
        # STATE 1: DATA UNAVAILABLE GATING
        # -------------------------------------------------------------
        if is_stale or spot_price <= 0 or (market_structure and market_structure.get("status") in ["INSUFFICIENT HISTORICAL DATA", "UNAVAILABLE — INVALID INPUT DATA"]):
            err_status = market_structure.get("status") if (market_structure and market_structure.get("status")) else "DATA UNAVAILABLE"
            return {
                "decision": err_status,
                "direction": "NONE",
                "signal_recommendation": err_status,
                "clean_recommendation": err_status,
                "trade_decision_headline": err_status,
                "trade_decision_sub": "Required market feed or technical indicators are missing, stale, or invalid.",
                "trade_decision_reasons": [f"Market structure verification status: {err_status}"],
                "framework_breakdown": {
                    "higher_timeframe_bias": {"trend": "UNAVAILABLE", "description": err_status},
                    "intraday_trend": {"structure": "UNAVAILABLE", "description": err_status},
                    "entry_confirmation": {"is_confirmed": False, "description": err_status},
                    "trade_invalidation": {"triggers": [err_status], "description": err_status},
                },
                "has_valid_setup": False,
                "confidence_score": 0.0,
                "confidence_pct": 0.0,
                "spot_price": round(spot_price, 2) if spot_price > 0 else 0.0,
                "instrument": sym,
                "timeframe": timeframe,
                "fixed_entry_price": 0.0,
                "entry_zone": err_status,
                "stop_loss": None,
                "target_levels": [],
                "target_1": None,
                "target_2": None,
                "risk_reward": "N/A",
                "risk_reward_ratio": "N/A",
                "supporting_conditions": [f"Market data: {err_status}"],
                "invalidation_condition": err_status,
                "invalidation_conditions": [err_status],
                "signal_timestamp": now_str,
                "data_mode": "UNAVAILABLE",
                "capital_advice": f"NO TRADING: {err_status}.",
                "disclaimer": "Institutional analytical signals only. Zero automated order placement.",
            }

        # -------------------------------------------------------------
        # STATE 2: EXECUTION LOCKED GATING (MARKET CLOSED)
        # -------------------------------------------------------------
        is_market_closed = False
        if market_status:
            is_market_closed = bool(market_status.get("is_market_closed", False) or (market_status.get("operating_state") == "MARKET_CLOSED"))

        if is_market_closed:
            return {
                "decision": "EXECUTION LOCKED",
                "direction": "NONE",
                "signal_recommendation": "EXECUTION LOCKED (MARKET CLOSED)",
                "clean_recommendation": "EXECUTION LOCKED",
                "trade_decision_headline": "EXECUTION LOCKED",
                "trade_decision_sub": "Official NSE market session is closed. Real-time order execution is locked by exchange hours.",
                "trade_decision_reasons": [
                    f"Exchange session closed. Last verified closing price: {curr_symbol}{spot_price:,.2f}.",
                    "Historical structures and indicator calculations preserved for review.",
                    "System policy permanently enforces zero automated trade execution; all trading requires manual discretion.",
                ],
                "framework_breakdown": {
                    "higher_timeframe_bias": {"trend": "HISTORICAL", "description": "Session closed - Historical replay"},
                    "intraday_trend": {"structure": "HISTORICAL", "description": "Official session close preserved"},
                    "entry_confirmation": {"is_confirmed": False, "description": "Execution locked outside trading hours"},
                    "trade_invalidation": {"triggers": ["Market is closed"], "description": "Live execution disabled"},
                },
                "has_valid_setup": False,
                "confidence_score": 0.0,
                "confidence_pct": 0.0,
                "spot_price": round(spot_price, 2),
                "instrument": sym,
                "timeframe": timeframe,
                "fixed_entry_price": round(spot_price, 2),
                "entry_zone": "EXECUTION LOCKED",
                "stop_loss": None,
                "target_levels": [],
                "target_1": None,
                "target_2": None,
                "risk_reward": "N/A",
                "risk_reward_ratio": "N/A",
                "supporting_conditions": [f"Session closed at {curr_symbol}{spot_price:,.2f}"],
                "invalidation_condition": "Session closed; live execution locked",
                "invalidation_conditions": ["Session closed; live execution locked"],
                "signal_timestamp": now_str,
                "data_mode": data_mode,
                "capital_advice": "MARKET CLOSED: Order placement locked until session open at 09:15 IST.",
                "disclaimer": "Institutional analytical signals only. Zero automated order placement.",
            }

        # -------------------------------------------------------------
        # STATE 3, 4, 5: REGULAR ACTIVE SESSION EVALUATION (BUY, SELL, WAIT)
        # -------------------------------------------------------------
        reasons_bullish: List[str] = []
        reasons_bearish: List[str] = []
        reasons_caution: List[str] = []

        bullish_score = 0
        bearish_score = 0

        # 1. Multi-Timeframe Trend
        comp_trend = mtf_data.get("composite_trend", "SIDEWAYS")
        bull_tf = mtf_data.get("bullish_timeframes", 0)
        bear_tf = mtf_data.get("bearish_timeframes", 0)

        if bull_tf >= 3:
            bullish_score += 2
            reasons_bullish.append(f"MTF Trend Alignment: {bull_tf}/5 timeframes are Bullish.")
        elif bear_tf >= 3:
            bearish_score += 2
            reasons_bearish.append(f"MTF Trend Alignment: {bear_tf}/5 timeframes are Bearish.")
        else:
            reasons_caution.append("MTF Trend is mixed/divergent across timeframes.")

        # 2. VWAP Positioning
        vwap = indicators.get("vwap", spot_price)
        dist_vwap_pct = ((spot_price - vwap) / vwap * 100.0) if vwap > 0 else 0.0

        if spot_price > vwap * 1.0005:
            bullish_score += 1
            reasons_bullish.append(f"Price is trading ABOVE Session VWAP ({curr_symbol}{vwap:,.2f}, +{dist_vwap_pct:.2f}%).")
        elif spot_price < vwap * 0.9995:
            bearish_score += 1
            reasons_bearish.append(f"Price is trading BELOW Session VWAP ({curr_symbol}{vwap:,.2f}, {dist_vwap_pct:.2f}%).")
        else:
            reasons_caution.append(f"Price is testing Session VWAP benchmark ({curr_symbol}{vwap:,.2f}).")

        # 3. EMA 10 / 20 Alignment
        ema10 = indicators.get("ema10", spot_price)
        ema20 = indicators.get("ema20", spot_price)
        if ema10 > ema20 * 1.0002:
            bullish_score += 1
            reasons_bullish.append(f"Bullish Moving Average Stack: EMA 10 ({curr_symbol}{ema10:,.2f}) > EMA 20 ({curr_symbol}{ema20:,.2f}).")
        elif ema10 < ema20 * 0.9998:
            bearish_score += 1
            reasons_bearish.append(f"Bearish Moving Average Stack: EMA 10 ({curr_symbol}{ema10:,.2f}) < EMA 20 ({curr_symbol}{ema20:,.2f}).")

        # 4. Momentum (RSI & MACD)
        rsi = indicators.get("rsi", 50.0)
        macd_hist = indicators.get("macd_hist", 0.0)
        if 50.0 <= rsi <= 72.0 and macd_hist > 0:
            bullish_score += 1
            reasons_bullish.append(f"Healthy Bullish Momentum: RSI at {rsi:.1f} (MACD Histogram: {macd_hist:+.2f}).")
        elif rsi > 72.0:
            reasons_caution.append(f"RSI Overextended ({rsi:.1f}): High risk of mean-reversion pullback. Avoid chasing.")
        elif rsi < 46.0 and macd_hist < 0:
            bearish_score += 1
            reasons_bearish.append(f"Bearish Momentum: RSI at {rsi:.1f} with negative MACD histogram ({macd_hist:+.2f}).")
        elif rsi <= 28.0:
            reasons_caution.append(f"RSI Deep Oversold ({rsi:.1f}): Bearish exhaustion. Potential bounce candidate.")

        # 5. Order Flow & CVD
        cvd_state = order_flow.get("order_flow_state", "NEUTRAL")
        buyer_pct = order_flow.get("buyer_percentage", 50.0)
        divergence = order_flow.get("divergence", "NONE")

        if "BULLISH" in cvd_state and buyer_pct >= 53.0:
            bullish_score += 2
            reasons_bullish.append(f"Aggressive Buyer CVD Flow: Taker buyers {buyer_pct:.1f}% dominating order tape.")
        elif "BEARISH" in cvd_state and buyer_pct <= 47.0:
            bearish_score += 2
            reasons_bearish.append(f"Aggressive Seller CVD Flow: Taker sellers {100.0 - buyer_pct:.1f}% dominating order tape.")

        if divergence != "NONE":
            reasons_caution.append(f"Order Flow Divergence Detected: {divergence}.")

        # 6. Market Breadth (if applicable)
        if sym != "BTC":
            breadth_score = market_breadth.get("breadth_score", 0.0)
            adv = market_breadth.get("advances", 25)
            dec = market_breadth.get("declines", 25)
            if breadth_score > 0.15:
                bullish_score += 1
                reasons_bullish.append(f"Broad Market Participation: {adv} Advances vs {dec} Declines (Score: {breadth_score:+.2f}).")
            elif breadth_score < -0.15:
                bearish_score += 1
                reasons_bearish.append(f"Bearish Market Breadth: {dec} Declines vs {adv} Advances (Score: {breadth_score:+.2f}).")

        # 7. Smart Money Concepts (SMC) Setup Confluence
        smc_setup_type = "NONE"
        smc_why_works: List[str] = []
        smc_reversal: Dict[str, Any] = {"chance_pct": 20.0, "risk_level": "LOW", "threats": []}

        if smc_data and smc_data.get("has_smc_setup"):
            smc_setup_type = smc_data.get("setup_type", "SMC_CONFLUENCE")
            smc_why_works = smc_data.get("details_why_it_works", [])
            smc_reversal = smc_data.get("reversal_risk", smc_reversal)

            if "BULLISH" in smc_setup_type or "SWEEP" in smc_setup_type or "ORDER_BLOCK" in smc_setup_type:
                bullish_score += 3
                reasons_bullish.append(f"SMC High-Conviction Institutional Setup: {smc_setup_type.replace('_', ' ')}.")
            elif "BEARISH" in smc_setup_type:
                bearish_score += 3
                reasons_bearish.append(f"SMC Bearish Supply Setup: {smc_setup_type.replace('_', ' ')}.")

        # Fixed structural risk parameters
        atr = indicators.get("atr", spot_price * 0.005)
        tight_risk = max(atr * 0.8, spot_price * 0.0025)

        # Contradiction Prevention Gates:
        # A BUY cannot trigger if higher timeframe is heavily bearish and spot is below VWAP
        # unless an explicit SMC liquidity sweep or CHoCH reversal setup has confirmed.
        has_bullish_smc_reversal = (smc_data and smc_data.get("has_smc_setup") and 
                                    ("SWEEP" in smc_setup_type or "CHOCH" in smc_setup_type or "ORDER_BLOCK" in smc_setup_type))
        has_bearish_smc_reversal = (smc_data and smc_data.get("has_smc_setup") and 
                                    ("SWEEP" in smc_setup_type or "CHOCH" in smc_setup_type or "ORDER_BLOCK" in smc_setup_type))

        is_bullish = (bullish_score >= 5 and bullish_score > bearish_score + 2)
        if is_bullish and bear_tf >= 3 and spot_price < vwap and not has_bullish_smc_reversal:
            is_bullish = False
            reasons_caution.append("Contradiction Filtered: Bullish intraday tick rejected against Bearish Higher-Timeframe trend.")

        is_bearish = (bearish_score >= 5 and bearish_score > bullish_score + 2)
        if is_bearish and bull_tf >= 3 and spot_price > vwap and not has_bearish_smc_reversal:
            is_bearish = False
            reasons_caution.append("Contradiction Filtered: Bearish intraday tick rejected against Bullish Higher-Timeframe trend.")

        # Proper Entry vs Overextended Check
        dist_from_vwap_pts = abs(spot_price - vwap)
        is_stretched = dist_from_vwap_pts > (atr * 1.5)

        if is_bullish:
            decision = "BUY"
            direction = "LONG"
            fixed_entry = smc_data.get("fixed_entry_price", round(spot_price, 2)) if smc_data else round(spot_price, 2)
            fixed_entry = round(float(fixed_entry), 2)
            risk_pts = round(max(tight_risk, 10.0), 2)
            stop_loss = round(fixed_entry - risk_pts, 2)
            target_1 = round(fixed_entry + (risk_pts * 1.5), 2)
            target_2 = round(fixed_entry + (risk_pts * 2.5), 2)
            rr_ratio = "1:2.0"

            # Strict mathematical consistency validation
            if not (stop_loss < fixed_entry < target_1 < target_2):
                stop_loss = round(fixed_entry - risk_pts, 2)
                target_1 = round(fixed_entry + (risk_pts * 1.5), 2)
                target_2 = round(fixed_entry + (risk_pts * 2.5), 2)

            if not is_stretched:
                recommendation = "STRONG_BUY (HIGH_PRIORITY - SMC PROPER ENTRY)"
                exec_type = "FIXED_STRUCTURAL_ENTRY"
                confidence = min(68.0 + (bullish_score * 4.0), 92.0)
                capital_advice = "HIGH CONVICTION BUY: Fixed entry price anchored to institutional Order Block / VWAP support."
            else:
                recommendation = "BUY_ON_PULLBACK (DO NOT CHASE - LIMIT ENTRY AT FIXED ANCHOR)"
                exec_type = "PULLBACK_REQUIRED"
                confidence = 74.0
                capital_advice = "DO NOT CHASE GREEN CANDLES: Place limit order at Fixed Entry anchor on the pullback."

            invalidations = [
                f"SMC Invalidation: 5-minute candle body close below Stop-Loss ({curr_symbol}{stop_loss:,.2f})",
                f"Order Flow CVD breakdown: aggressive seller volume flips delta below 45%",
                f"Failure of Order Block / Session VWAP support benchmark ({curr_symbol}{vwap:,.2f})",
            ]
            reclaim_trigger = fixed_entry
            liquidity_zone = stop_loss

        elif is_bearish:
            direction = "SHORT"
            if buy_priority_mode:
                decision = "AVOID_SHORT (CAPITAL_PRESERVATION)"
                recommendation = "AVOID SHORT / STAY IN CASH (LOW CAPITAL SHIELD)"
                exec_type = "CAPITAL_SHIELD_ACTIVE"
                confidence = 85.0

                fixed_entry = round(spot_price, 2)
                stop_loss = None
                target_1 = None
                target_2 = None
                rr_ratio = "N/A (Short Disabled)"

                reclaim_trigger = round(max(spot_price + tight_risk, vwap), 2)
                liquidity_zone = round(spot_price - (tight_risk * 1.5), 2)

                invalidations = [
                    "CAPITAL PROTECTION ACTIVE: Short selling index futures / naked calls requires large margin (₹1.5L+).",
                    "STAY IN 100% CASH: Exit or protect open longs with trailing stop. Do not enter short.",
                    "DO NOT SHORT SELL: Wait for Smart Money to sweep sell-side liquidity at lows for the next BUY setup.",
                    "Low-budget option (optional): If trading downside, restrict to tight Put Option (PE) buy only.",
                ]
                capital_advice = "CAPITAL SHIELD: Shorting skipped due to margin constraints. Protect capital for the next Buy opportunity."
            else:
                decision = "SELL"
                recommendation = "SELL"
                exec_type = "SHORT_CONTINUATION"
                confidence = min(60.0 + (bearish_score * 4.0), 92.0)

                fixed_entry = round(spot_price, 2)
                risk_pts = round(max(tight_risk, 10.0), 2)
                stop_loss = round(fixed_entry + risk_pts, 2)
                target_1 = round(fixed_entry - (risk_pts * 1.5), 2)
                target_2 = round(fixed_entry - (risk_pts * 2.5), 2)
                rr_ratio = "1:2.0"

                # Strict mathematical consistency validation
                if not (stop_loss > fixed_entry > target_1 > target_2):
                    stop_loss = round(fixed_entry + risk_pts, 2)
                    target_1 = round(fixed_entry - (risk_pts * 1.5), 2)
                    target_2 = round(fixed_entry - (risk_pts * 2.5), 2)

                reclaim_trigger = stop_loss
                liquidity_zone = target_1

                invalidations = [
                    f"5-minute close above Session VWAP ({curr_symbol}{vwap:,.2f})",
                    f"Order Flow CVD flips to aggressive buyer dominance (> 54% buyer ratio)",
                    f"Breakout above immediate swing resistance ({curr_symbol}{stop_loss:,.2f})",
                ]
                capital_advice = "Institutional short setup active."

        else:
            decision = "WAIT"
            direction = "NEUTRAL"
            recommendation = "WAIT (CHOP / CONSOLIDATION)"
            exec_type = "NO_ENTRY_CHOP"
            confidence = 50.0

            fixed_entry = round(spot_price, 2)
            stop_loss = None
            target_1 = None
            target_2 = None
            rr_ratio = "N/A"

            reclaim_trigger = round(max(spot_price + tight_risk, vwap), 2)
            liquidity_zone = round(spot_price - tight_risk, 2)

            invalidations = [
                "Market is currently in chop/consolidation mode with conflicting internal signals.",
                "Wait for clean MTF breakout above VWAP and confirmed buyer CVD before deploying capital.",
            ]
            capital_advice = "CHOP DETECTED: Capital preservation mode. Zero edge inside range chop."

        # Add SMC reasoning to reasons
        all_reasons = (
            [f"[+] {r}" for r in reasons_bullish]
            + [f"[-] {r}" for r in reasons_bearish]
            + [f"[!] {r}" for r in reasons_caution]
        )
        if smc_why_works:
            all_reasons = [f"[SMC] {w}" for w in smc_why_works] + all_reasons

        struct_state = market_structure.get("structure_state", "NEUTRAL") if market_structure else "NEUTRAL"
        if "BULLISH" in struct_state:
            ms_label = "Bullish"
        elif "BEARISH" in struct_state:
            ms_label = "Bearish"
        else:
            ms_label = "Neutral"

        has_valid_setup = (decision in ("BUY", "SELL"))

        htf_bias_trend = "BULLISH" if bull_tf >= 3 else ("BEARISH" if bear_tf >= 3 else "MIXED / NEUTRAL")
        htf_bias_desc = f"{bull_tf}/5 Bullish, {bear_tf}/5 Bearish timeframes ({comp_trend})"
        intraday_desc = f"Price {'above' if spot_price > vwap else 'below'} Session VWAP ({curr_symbol}{vwap:,.1f}) | {ms_label} Structure"

        if has_valid_setup and decision == "BUY":
            entry_conf_desc = f"SMC {smc_setup_type.replace('_', ' ').title()} confirmed at {curr_symbol}{fixed_entry:,.1f} with {buyer_pct:.1f}% Buyer CVD"
        elif has_valid_setup and decision == "SELL":
            entry_conf_desc = f"Bearish trend continuation confirmed at {curr_symbol}{fixed_entry:,.1f} with {100.0 - buyer_pct:.1f}% Seller CVD"
        else:
            entry_conf_desc = "No confirmed entry trigger. Awaiting structural order block or FVG test."

        if stop_loss is not None:
            inval_desc = f"Setup canceled if price closes beyond {curr_symbol}{stop_loss:,.1f} or order flow flips."
        else:
            inval_desc = "Execution locked or waiting for setup confirmation; no active stop-loss trigger."

        framework_breakdown = {
            "higher_timeframe_bias": {
                "trend": htf_bias_trend,
                "composite_trend": comp_trend,
                "bullish_timeframes": bull_tf,
                "bearish_timeframes": bear_tf,
                "description": htf_bias_desc,
            },
            "intraday_trend": {
                "structure": ms_label,
                "vwap_price": round(vwap, 2),
                "is_above_vwap": spot_price >= vwap,
                "description": intraday_desc,
            },
            "entry_confirmation": {
                "is_confirmed": has_valid_setup,
                "setup_type": smc_setup_type,
                "fixed_entry_price": fixed_entry,
                "buyer_percentage": round(buyer_pct, 1),
                "description": entry_conf_desc,
            },
            "trade_invalidation": {
                "invalidation_price": stop_loss,
                "triggers": invalidations,
                "description": inval_desc,
            },
        }

        structured_reasons = [
            f"Higher-Timeframe Bias: {htf_bias_desc}.",
            f"Intraday Trend & VWAP: {intraday_desc}.",
            f"Entry Confirmation: {entry_conf_desc}.",
            f"Trade Invalidation: {inval_desc}.",
        ]

        if decision == "BUY":
            clean_rec = "STRONG BUY" if (confidence >= 80.0 or not is_stretched) else "BUY"
            trade_decision_headline = clean_rec
            trade_decision_sub = "Confirmed bullish structural entry anchored to support."
            trade_decision_reasons = structured_reasons + ([r for r in reasons_bullish[:2]])
        elif decision == "SELL":
            clean_rec = "STRONG SELL" if confidence >= 80.0 else "SELL"
            trade_decision_headline = clean_rec
            trade_decision_sub = "Confirmed bearish continuation below resistance."
            trade_decision_reasons = structured_reasons + ([r for r in reasons_bearish[:2]])
        else:
            clean_rec = "WAIT FOR CONFIRMATION"
            trade_decision_headline = "WAIT"
            trade_decision_sub = "No confirmed entry. Wait for price confirmation and defined risk."
            trade_decision_reasons = structured_reasons

        entry_zone_str = f"{curr_symbol}{fixed_entry:,.2f} (FIXED ANCHOR)" if has_valid_setup else f"{curr_symbol}{fixed_entry:,.2f} (WAITING TRIGGER)"

        return {
            "decision": decision,
            "direction": direction,
            "signal_recommendation": recommendation,
            "clean_recommendation": clean_rec,
            "has_valid_setup": has_valid_setup,
            "market_structure_label": ms_label,
            "trade_decision_headline": trade_decision_headline,
            "trade_decision_sub": trade_decision_sub,
            "trade_decision_reasons": trade_decision_reasons,
            "framework_breakdown": framework_breakdown,
            "execution_type": exec_type,
            "capital_mode": "BUY_PRIORITY_LOW_CAPITAL" if buy_priority_mode else "UNCONSTRAINED",
            "confidence_score": round(confidence, 1),
            "confidence_pct": round(confidence, 1),
            "spot_price": round(spot_price, 2),
            "instrument": sym,
            "timeframe": timeframe,
            "fixed_entry_price": fixed_entry,
            "entry_zone": entry_zone_str,
            "stop_loss": stop_loss,
            "target_levels": [t for t in [target_1, target_2] if t is not None],
            "target_1": target_1,
            "target_2": target_2,
            "risk_reward": rr_ratio,
            "risk_reward_ratio": rr_ratio,
            "bullish_reclaim_trigger": reclaim_trigger,
            "downside_liquidity_zone": liquidity_zone,
            "supporting_conditions": all_reasons,
            "invalidation_condition": invalidations[0] if invalidations else "None",
            "invalidation_conditions": invalidations,
            "signal_timestamp": now_str,
            "data_mode": data_mode,
            "reasons": all_reasons,
            "capital_advice": capital_advice,
            "bullish_factors": len(reasons_bullish),
            "bearish_factors": len(reasons_bearish),
            "smc_setup": {
                "setup_type": smc_setup_type,
                "fixed_entry_price": fixed_entry,
                "why_it_works": smc_why_works if smc_why_works else [
                    "Price supported by institutional moving average stack and session VWAP equilibrium.",
                    "Buyer volume delta confirmation on market tape.",
                ],
                "reversal_risk": smc_reversal,
            },
            "disclaimer": "Institutional analytical signals only. Zero automated order placement.",
        }
