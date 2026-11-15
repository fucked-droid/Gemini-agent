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
"""

import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("TradingDecisionEngine")

class TradingDecisionEngine:
    """
    Configurable rules-based multi-factor decision engine with Smart Money Concepts (SMC),
    Fixed Structural Entry Points, and Low-Capital Protection.
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
    ) -> Dict[str, Any]:
        """
        Synthesizes market internals, SMC structures, and order flow.
        Calculates a FIXED structural entry point, why the setup works, and reversal risk.
        """
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
            reasons_bullish.append(f"Price is trading ABOVE Session VWAP (₹{vwap:,.2f}, +{dist_vwap_pct:.2f}%).")
        elif spot_price < vwap * 0.9995:
            bearish_score += 1
            reasons_bearish.append(f"Price is trading BELOW Session VWAP (₹{vwap:,.2f}, {dist_vwap_pct:.2f}%).")
        else:
            reasons_caution.append(f"Price is testing Session VWAP benchmark (₹{vwap:,.2f}).")

        # 3. EMA 10 / 20 Alignment
        ema10 = indicators.get("ema10", spot_price)
        ema20 = indicators.get("ema20", spot_price)
        if ema10 > ema20 * 1.0002:
            bullish_score += 1
            reasons_bullish.append(f"Bullish Moving Average Stack: EMA 10 (₹{ema10:,.2f}) > EMA 20 (₹{ema20:,.2f}).")
        elif ema10 < ema20 * 0.9998:
            bearish_score += 1
            reasons_bearish.append(f"Bearish Moving Average Stack: EMA 10 (₹{ema10:,.2f}) < EMA 20 (₹{ema20:,.2f}).")

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

        # 6. Market Breadth
        breadth_score = market_breadth.get("breadth_score", 0.0)
        adv = market_breadth.get("advances", 25)
        dec = market_breadth.get("declines", 25)
        if breadth_score > 0.15:
            bullish_score += 1
            reasons_bullish.append(f"Broad Market Participation: {adv} Advances vs {dec} Declines (Score: {breadth_score:+.2f}).")
        elif breadth_score < -0.15:
            bearish_score += 1
            reasons_bearish.append(f"Weak Market Breadth: {dec} Declines vs {adv} Advances (Score: {breadth_score:+.2f}).")

        # 7. Market Structure & Swings
        struct_state = market_structure.get("structure_state", "NEUTRAL")
        event = market_structure.get("event", "NONE")
        if "BULLISH" in struct_state:
            bullish_score += 1
            reasons_bullish.append(f"Market Structure: Higher-High / Higher-Low Bullish Expansion ({event}).")
        elif "BEARISH" in struct_state:
            bearish_score += 1
            reasons_bearish.append(f"Market Structure: Lower-High / Lower-Low Bearish Expansion ({event}).")

        # ATR & Risk Geometry
        atr = indicators.get("atr", spot_price * 0.005)
        tight_risk = max(atr * 0.65, spot_price * 0.002)

        # 8. Smart Money Concepts (SMC) Integration
        has_smc = smc_data is not None and smc_data.get("has_smc_setup", False)
        smc_setup_type = smc_data.get("setup_type", "NO_SMC_SETUP") if has_smc else "TECHNICAL_STRUCTURE"
        smc_why_works = smc_data.get("details_why_it_works", []) if has_smc else []
        smc_reversal = smc_data.get("reversal_risk", {}) if has_smc else {}

        # ==========================================================
        # DECISION LOGIC: HIGH-PRIORITY BUY & FIXED STRUCTURAL ENTRY
        # ==========================================================
        is_bullish = (bullish_score >= 5 and bearish_score <= 1)
        is_bearish = (bearish_score >= 5 and bullish_score <= 1)

        is_stretched = (spot_price > ema10 + (atr * 0.45)) or (rsi > 72.0)

        # Build Reversal Risk object
        if not smc_reversal:
            rev_chance = 25.0
            rev_threats = []
            if rsi > 70.0:
                rev_chance += 20.0
                rev_threats.append(f"RSI Overextended ({rsi:.1f}): Near-term mean-reversion threat.")
            if ema10 < ema20:
                rev_chance += 15.0
                rev_threats.append("EMA 10 < EMA 20: Counter-trend pullback risk.")
            if not rev_threats:
                rev_threats.append("No immediate structural barriers detected below target.")

            smc_reversal = {
                "chance_pct": min(rev_chance, 75.0),
                "risk_level": "LOW" if rev_chance < 35.0 else ("MODERATE" if rev_chance <= 55.0 else "HIGH"),
                "threats": rev_threats,
                "invalidation_trigger": f"Candle close below Stop-Loss at ₹{round(spot_price - tight_risk, 2):,.2f}.",
            }

        if is_bullish:
            # FIXED STRUCTURAL ENTRY DETERMINATION
            if has_smc and smc_data.get("fixed_entry_price", 0.0) > 0:
                fixed_entry = smc_data["fixed_entry_price"]
                stop_loss = smc_data["fixed_stop_loss"]
                target_1 = smc_data["fixed_target_1"]
                target_2 = smc_data["fixed_target_2"]
                rr_ratio = smc_data.get("risk_reward_ratio", "1:2.0")
            else:
                # Fixed anchor to VWAP or EMA10 support benchmark (NOT moving with every tick)
                fixed_entry = round(max(vwap, ema10 - (atr * 0.10)), 2)
                stop_loss = round(min(fixed_entry - tight_risk, vwap * 0.999), 2)
                risk_pts = max(fixed_entry - stop_loss, spot_price * 0.003)
                target_1 = round(spot_price + (risk_pts * 1.5), 2)
                target_2 = round(spot_price + (risk_pts * 2.5), 2)
                rr_ratio = "1:2.0"

            if not is_stretched:
                decision = "BUY"
                recommendation = "STRONG_BUY (HIGH_PRIORITY - SMC PROPER ENTRY)"
                exec_type = "FIXED_STRUCTURAL_ENTRY"
                confidence = min(68.0 + (bullish_score * 4.0), 96.0)
                capital_advice = "HIGH CONVICTION BUY: Fixed entry price anchored to institutional Order Block / VWAP support."
            else:
                decision = "BUY"
                recommendation = "BUY_ON_PULLBACK (DO NOT CHASE - LIMIT ENTRY AT FIXED ANCHOR)"
                exec_type = "PULLBACK_REQUIRED"
                confidence = 74.0
                capital_advice = "DO NOT CHASE GREEN CANDLES: Place limit order at Fixed Entry anchor on the pullback."

            invalidations = [
                f"SMC Invalidation: 5-minute candle body close below Stop-Loss (₹{stop_loss:,.2f})",
                f"Order Flow CVD breakdown: aggressive seller volume flips delta below 45%",
                f"Failure of Order Block / Session VWAP support benchmark (₹{vwap:,.2f})",
            ]
            reclaim_trigger = fixed_entry
            liquidity_zone = stop_loss

        elif is_bearish:
            if buy_priority_mode:
                # LOW CAPITAL MODE: Prevent expensive/risky short selling!
                decision = "AVOID_SHORT (CAPITAL_PRESERVATION)"
                recommendation = "AVOID SHORT / STAY IN CASH (LOW CAPITAL SHIELD)"
                exec_type = "CAPITAL_SHIELD_ACTIVE"
                confidence = 85.0

                fixed_entry = round(spot_price, 2)
                stop_loss = round(spot_price + tight_risk, 2)
                target_1 = round(spot_price - (tight_risk * 1.5), 2)
                target_2 = round(spot_price - (tight_risk * 2.5), 2)
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
                # UNCONSTRAINED INSTITUTIONAL SHORT MODE
                decision = "SELL"
                recommendation = "SELL"
                exec_type = "SHORT_CONTINUATION"
                confidence = min(60.0 + (bearish_score * 4.0), 92.0)

                fixed_entry = round(spot_price, 2)
                stop_loss = round(max(spot_price + tight_risk, vwap * 1.001), 2)
                risk_pts = stop_loss - spot_price
                target_1 = round(spot_price - (risk_pts * 1.5), 2)
                target_2 = round(spot_price - (risk_pts * 2.5), 2)
                rr_ratio = "1:2.0"

                reclaim_trigger = stop_loss
                liquidity_zone = target_1

                invalidations = [
                    f"5-minute close above Session VWAP (₹{vwap:,.2f})",
                    f"Order Flow CVD flips to aggressive buyer dominance (> 54% buyer ratio)",
                    f"Breakout above immediate swing resistance (₹{stop_loss:,.2f})",
                ]
                capital_advice = "Institutional short setup active."

        else:
            decision = "WAIT"
            recommendation = "WAIT (CHOP / CONSOLIDATION)"
            exec_type = "NO_ENTRY_CHOP"
            confidence = 50.0

            fixed_entry = round(spot_price, 2)
            stop_loss = round(spot_price - tight_risk, 2)
            target_1 = round(spot_price + (tight_risk * 1.5), 2)
            target_2 = round(spot_price + (tight_risk * 2.5), 2)
            rr_ratio = "1:1.5"

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

        # Clean 5-State Recommendation & Market Structure Mapping
        struct_state = market_structure.get("structure_state", "NEUTRAL") if market_structure else "NEUTRAL"
        if "BULLISH" in struct_state:
            ms_label = "Bullish"
        elif "BEARISH" in struct_state:
            ms_label = "Bearish"
        else:
            ms_label = "Neutral"

        if decision == "BUY":
            has_valid_setup = True
            clean_rec = "STRONG BUY" if (confidence >= 80.0 or not is_stretched) else "BUY"
            trade_decision_headline = clean_rec
            trade_decision_sub = "Confirmed bullish structural entry anchored to support."
            trade_decision_reasons = (
                [r for r in reasons_bullish]
                + (smc_why_works if smc_why_works else [])
            )
        elif decision == "SELL":
            has_valid_setup = True
            clean_rec = "STRONG SELL" if confidence >= 80.0 else "SELL"
            trade_decision_headline = clean_rec
            trade_decision_sub = "Confirmed bearish continuation below resistance."
            trade_decision_reasons = [r for r in reasons_bearish]
        else:
            has_valid_setup = False
            clean_rec = "WAIT FOR CONFIRMATION"
            trade_decision_headline = "WAIT"
            trade_decision_sub = "No confirmed entry. Wait for price confirmation and defined risk."
            trade_decision_reasons = []
            if spot_price < vwap:
                trade_decision_reasons.append(f"Price (₹{spot_price:,.2f}) trading below Session VWAP benchmark (₹{vwap:,.2f}).")
            elif spot_price > vwap and is_stretched:
                trade_decision_reasons.append("Price extended above entry anchor; awaiting confirmed pullback before committing capital.")
            if "EXPANSION" not in struct_state:
                trade_decision_reasons.append(f"Market structure is in {struct_state.replace('_', ' ').title()}; awaiting clear Break of Structure.")
            if reasons_caution:
                trade_decision_reasons.extend(reasons_caution[:2])
            if buy_priority_mode and is_bearish:
                trade_decision_reasons.append("Capital preservation mode active: Short selling skipped due to margin requirements.")
            if not trade_decision_reasons:
                trade_decision_reasons.append("Chop/consolidation detected with conflicting multi-timeframe directional signals.")

        # Format Fixed Entry Display
        entry_zone_str = f"₹{fixed_entry:,.2f} (FIXED ANCHOR)"

        return {
            "decision": decision,
            "signal_recommendation": recommendation,
            "clean_recommendation": clean_rec,
            "has_valid_setup": has_valid_setup,
            "market_structure_label": ms_label,
            "trade_decision_headline": trade_decision_headline,
            "trade_decision_sub": trade_decision_sub,
            "trade_decision_reasons": trade_decision_reasons,
            "execution_type": exec_type,
            "capital_mode": "BUY_PRIORITY_LOW_CAPITAL" if buy_priority_mode else "UNCONSTRAINED",
            "confidence_pct": round(confidence, 1),
            "spot_price": round(spot_price, 2),
            "fixed_entry_price": fixed_entry,
            "entry_zone": entry_zone_str,
            "stop_loss": stop_loss,
            "target_1": target_1,
            "target_2": target_2,
            "risk_reward_ratio": rr_ratio,
            "bullish_reclaim_trigger": reclaim_trigger,
            "downside_liquidity_zone": liquidity_zone,
            "invalidation_conditions": invalidations,
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
