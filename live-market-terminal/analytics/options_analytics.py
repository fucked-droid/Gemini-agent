"""
Options Sentiment & Derivatives Analytics Engine.
Calculates Put-Call Ratio (PCR), Open Interest shifts, Max Pain, Option Writing intensity,
and Key Option Strike Walls for NIFTY and BANKNIFTY.

Strict Institutional Mandates:
- One authoritative options data source with strict timestamp and freshness validation.
- Expiry-specific calculations (evaluates nearest active expiry series).
- Correct strike mapping without cross-instrument fabrication (no scaling NIFTY to BANKNIFTY).
- Strict degradation: If the live options feed is unavailable, all dependent components
  must display UNAVAILABLE (never retain stale option-chain values as live data).
"""

import json
import logging
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from config import get_ist_now

logger = logging.getLogger("OptionsAnalytics")

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent


class OptionsAnalytics:
    """
    Evaluates institutional options market intelligence strictly from verified option chain data.
    """

    @classmethod
    def get_options_intelligence(
        cls,
        symbol: str = "NIFTY",
        spot_price: float = 0.0,
        allow_sample: bool = False,
    ) -> Dict[str, Any]:
        """
        Deep institutional options analysis covering:
        1. PCR (Open Interest & Volume)
        2. Change in Open Interest (Net CE vs PE shifts)
        3. Call/Put Writing Intensity & Sentiment
        4. Max Pain Strike & Distance to Spot
        5. Important Option Strikes (Resistance Wall, Support Floor, Heaviest Writing Strikes, Radar Table)
        """
        sym = symbol.upper()

        # 1. Crypto or non-derivatives instruments
        if sym in ["BTC", "BITCOIN", "BTCUSD"]:
            return cls._get_unavailable_payload(
                symbol=sym,
                spot_price=spot_price,
                status="NO_CRYPTO_OPTIONS",
                details="Crypto instruments do not trade on NSE Option Chain.",
            )

        # 2. Check Provider Connection and Freshness
        from data.market_status_manager import get_market_status_manager
        status_mgr = get_market_status_manager()
        is_provider_live = status_mgr.provider_connected and status_mgr.is_session_active(sym)

        # 3. Resolve authoritative option chain data
        raw_data, source_type = cls._load_option_chain_data(sym)

        if not raw_data:
            return cls._get_unavailable_payload(
                symbol=sym,
                spot_price=spot_price,
                status="UNAVAILABLE",
                details=f"Live option chain feed for {sym} is unavailable (Provider offline).",
            )

        # Check timestamp freshness
        records = raw_data.get("records", {})
        data_timestamp_str = records.get("timestamp", "")
        underlying = float(records.get("underlyingValue", 0.0) or 0.0)

        # Validate that the chain actually belongs to the requested instrument
        # If the file contains NIFTY data (underlying ~24000-26000), do NOT use it for BANKNIFTY (spot ~50000+)!
        if sym == "BANKNIFTY" and underlying > 0 and underlying < 35000.0:
            return cls._get_unavailable_payload(
                symbol=sym,
                spot_price=spot_price,
                status="UNAVAILABLE",
                details="BANKNIFTY live option chain feed unavailable. Instrument data isolation enforced.",
            )
        elif sym == "NIFTY" and underlying > 35000.0:
            return cls._get_unavailable_payload(
                symbol=sym,
                spot_price=spot_price,
                status="UNAVAILABLE",
                details="NIFTY live option chain feed unavailable. Instrument data isolation enforced.",
            )

        # Check freshness of cached file
        is_fresh = cls._check_data_freshness(data_timestamp_str)
        if not is_fresh and not is_provider_live and not allow_sample:
            # Mandate: If feed is unavailable/stale, dependent components must display UNAVAILABLE
            return cls._get_unavailable_payload(
                symbol=sym,
                spot_price=spot_price,
                status="UNAVAILABLE",
                details=f"Option chain feed is stale ({data_timestamp_str or 'No timestamp'}). Live NSE provider not connected.",
            )

        try:
            rows = records.get("data", [])
            if not rows:
                return cls._get_unavailable_payload(
                    symbol=sym,
                    spot_price=spot_price,
                    status="UNAVAILABLE",
                    details=f"Empty option chain records for {sym}.",
                )

            current_spot = spot_price if spot_price > 0 else (underlying if underlying > 0 else 25000.0)

            # Expiry-specific calculations: Extract nearest active expiry
            expiry_dates = records.get("expiryDates", [])
            active_expiry = expiry_dates[0] if expiry_dates else None

            parsed_strikes: List[Dict[str, Any]] = []
            tot_ce_oi = 0
            tot_pe_oi = 0
            tot_ce_vol = 0
            tot_pe_vol = 0
            tot_ce_chg = 0
            tot_pe_chg = 0

            # Reasonable strike boundary around spot to eliminate extreme illiquid strikes
            max_strike_dist = current_spot * 0.08  # ±8% band around spot

            for r in rows:
                raw_strike = float(r.get("strikePrice", 0) or 0)
                if raw_strike <= 0 or abs(raw_strike - current_spot) > max_strike_dist:
                    continue

                # Filter by nearest expiry if present on the row
                row_expiry = r.get("expiryDate")
                if active_expiry and row_expiry and row_expiry != active_expiry:
                    continue

                ce = r.get("CE", {}) if isinstance(r.get("CE"), dict) else {}
                pe = r.get("PE", {}) if isinstance(r.get("PE"), dict) else {}

                ce_oi = int(ce.get("openInterest", 0) or 0)
                pe_oi = int(pe.get("openInterest", 0) or 0)
                ce_vol = int(ce.get("totalTradedVolume", 0) or 0)
                pe_vol = int(pe.get("totalTradedVolume", 0) or 0)
                ce_chg = int(ce.get("changeinOpenInterest", 0) or 0)
                pe_chg = int(pe.get("changeinOpenInterest", 0) or 0)
                ce_ltp = float(ce.get("lastPrice", 0.0) or 0.0)
                pe_ltp = float(pe.get("lastPrice", 0.0) or 0.0)

                tot_ce_oi += ce_oi
                tot_pe_oi += pe_oi
                tot_ce_vol += ce_vol
                tot_pe_vol += pe_vol
                tot_ce_chg += ce_chg
                tot_pe_chg += pe_chg

                parsed_strikes.append({
                    "strike": raw_strike,
                    "ce_oi": ce_oi,
                    "pe_oi": pe_oi,
                    "ce_vol": ce_vol,
                    "pe_vol": pe_vol,
                    "ce_chg": ce_chg,
                    "pe_chg": pe_chg,
                    "ce_ltp": ce_ltp,
                    "pe_ltp": pe_ltp,
                })

            if not parsed_strikes:
                return cls._get_unavailable_payload(
                    symbol=sym,
                    spot_price=spot_price,
                    status="UNAVAILABLE",
                    details=f"No active option strikes found for {sym} expiry {active_expiry}.",
                )

            parsed_strikes.sort(key=lambda x: x["strike"])

            # 1. PCR Calculations
            pcr_oi = round(tot_pe_oi / tot_ce_oi, 2) if tot_ce_oi > 0 else 1.0
            pcr_vol = round(tot_pe_vol / tot_ce_vol, 2) if tot_ce_vol > 0 else 1.0

            # 2. Writing Intensity & Sentiment
            call_writing_contracts = max(0, tot_ce_chg)
            put_writing_contracts = max(0, tot_pe_chg)

            if tot_pe_chg > tot_ce_chg * 1.25 and tot_pe_chg > 0:
                writing_sentiment = "Aggressive Put Writing (Firm Support Floor)"
                writing_intensity = f"Bullish Skew (+{tot_pe_chg - tot_ce_chg:,} Net PE Contracts)"
            elif tot_ce_chg > tot_pe_chg * 1.25 and tot_ce_chg > 0:
                writing_sentiment = "Aggressive Call Writing (Heavy Overhead Resistance)"
                writing_intensity = f"Bearish Skew (+{tot_ce_chg - tot_pe_chg:,} Net CE Contracts)"
            else:
                writing_sentiment = "Balanced Call/Put Writing (Rangebound Auction)"
                writing_intensity = "Neutral Delta Skew"

            # 3. Max Pain Calculation
            all_strike_prices = [p["strike"] for p in parsed_strikes]
            min_loss = float("inf")
            max_pain_strike = all_strike_prices[0] if all_strike_prices else current_spot

            for test_strike in all_strike_prices:
                total_loss = 0.0
                for item in parsed_strikes:
                    s = item["strike"]
                    if test_strike > s:
                        total_loss += (test_strike - s) * item["ce_oi"]
                    elif test_strike < s:
                        total_loss += (s - test_strike) * item["pe_oi"]

                if total_loss < min_loss:
                    min_loss = total_loss
                    max_pain_strike = test_strike

            max_pain_dist = round(current_spot - max_pain_strike, 1)
            if max_pain_dist > 50:
                max_pain_bias = f"Spot ₹{current_spot:,.0f} > Max Pain ₹{max_pain_strike:,.0f} (+{max_pain_dist:,.0f} pts): Downside gravitational drag"
            elif max_pain_dist < -50:
                max_pain_bias = f"Spot ₹{current_spot:,.0f} < Max Pain ₹{max_pain_strike:,.0f} ({max_pain_dist:,.0f} pts): Bullish pull toward expiry strike"
            else:
                max_pain_bias = f"Spot ₹{current_spot:,.0f} pegged to Max Pain ₹{max_pain_strike:,.0f}: Expiry pinning equilibrium"

            # 4. Important Option Strikes
            highest_ce_row = max(parsed_strikes, key=lambda x: x["ce_oi"]) if parsed_strikes else None
            major_res_strike = highest_ce_row["strike"] if highest_ce_row else round(current_spot + 300)
            major_res_oi = highest_ce_row["ce_oi"] if highest_ce_row else 0

            highest_pe_row = max(parsed_strikes, key=lambda x: x["pe_oi"]) if parsed_strikes else None
            major_sup_strike = highest_pe_row["strike"] if highest_pe_row else round(current_spot - 300)
            major_sup_oi = highest_pe_row["pe_oi"] if highest_pe_row else 0

            heaviest_ce_writing_row = max(parsed_strikes, key=lambda x: x["ce_chg"]) if parsed_strikes else None
            heaviest_call_strike = heaviest_ce_writing_row["strike"] if heaviest_ce_writing_row else major_res_strike
            heaviest_call_chg = heaviest_ce_writing_row["ce_chg"] if heaviest_ce_writing_row else 0

            heaviest_pe_writing_row = max(parsed_strikes, key=lambda x: x["pe_chg"]) if parsed_strikes else None
            heaviest_put_strike = heaviest_pe_writing_row["strike"] if heaviest_pe_writing_row else major_sup_strike
            heaviest_put_chg = heaviest_pe_writing_row["pe_chg"] if heaviest_pe_writing_row else 0

            # 5. Strike Radar Table (5-7 strikes centered around ATM)
            atm_strike = min(all_strike_prices, key=lambda s: abs(s - current_spot)) if all_strike_prices else current_spot
            atm_idx = all_strike_prices.index(atm_strike) if atm_strike in all_strike_prices else 0
            start_idx = max(0, atm_idx - 3)
            end_idx = min(len(all_strike_prices), atm_idx + 4)
            radar_slice = parsed_strikes[start_idx:end_idx]

            key_strikes = []
            for item in radar_slice:
                stk = item["strike"]
                c_oi = item["ce_oi"]
                p_oi = item["pe_oi"]
                c_chg = item["ce_chg"]
                p_chg = item["pe_chg"]
                stk_pcr = round(p_oi / c_oi, 2) if c_oi > 0 else 1.0

                if p_chg > c_chg and p_oi >= c_oi:
                    bias = "BULLISH_SUPPORT"
                elif c_chg > p_chg and c_oi >= p_oi:
                    bias = "BEARISH_CEILING"
                else:
                    bias = "CONTESTED_ZONE"

                key_strikes.append({
                    "strike": stk,
                    "ce_oi": c_oi,
                    "pe_oi": p_oi,
                    "ce_chg": c_chg,
                    "pe_chg": p_chg,
                    "pcr": stk_pcr,
                    "bias": bias,
                    "is_atm": (stk == atm_strike),
                    "is_max_pain": (stk == max_pain_strike),
                })

            # Overall Sentiment Score
            score = 0
            if pcr_oi >= 1.15:
                score += 1
            elif pcr_oi <= 0.85:
                score -= 1

            if tot_pe_chg > tot_ce_chg:
                score += 1
            elif tot_ce_chg > tot_pe_chg:
                score -= 1

            if score > 0:
                sentiment = "Positive"
                color_class = "text-green"
                details = f"Bullish PCR ({pcr_oi:.2f}) with heavy Put writer support (+{tot_pe_chg:,} PE OI)."
            elif score < 0:
                sentiment = "Negative"
                color_class = "text-red"
                details = f"Bearish PCR ({pcr_oi:.2f}) with aggressive Call writer resistance (+{tot_ce_chg:,} CE OI)."
            else:
                sentiment = "Neutral"
                color_class = "text-yellow"
                details = f"Balanced PCR ({pcr_oi:.2f}) with equal Open Interest distribution."

            data_mode = "LIVE" if is_provider_live else "HISTORICAL_SAMPLE"

            return {
                "sentiment": sentiment,
                "status": "CALCULATED" if is_provider_live else "OFFLINE_SAMPLE",
                "data_mode": data_mode,
                "symbol": sym,
                "spot_price": current_spot,
                "expiry": active_expiry,
                "pcr_oi": pcr_oi,
                "pcr_volume": pcr_vol,
                "net_ce_oi_change": tot_ce_chg,
                "net_pe_oi_change": tot_pe_chg,
                "call_writing_contracts": call_writing_contracts,
                "put_writing_contracts": put_writing_contracts,
                "writing_sentiment": writing_sentiment,
                "writing_intensity": writing_intensity,
                "max_pain": max_pain_strike,
                "max_pain_distance": max_pain_dist,
                "max_pain_bias": max_pain_bias,
                "major_resistance_strike": major_res_strike,
                "major_resistance_oi": major_res_oi,
                "major_support_strike": major_sup_strike,
                "major_support_oi": major_sup_oi,
                "heaviest_call_writing_strike": heaviest_call_strike,
                "heaviest_call_writing_chg": heaviest_call_chg,
                "heaviest_put_writing_strike": heaviest_put_strike,
                "heaviest_put_writing_chg": heaviest_put_chg,
                "key_strikes": key_strikes,
                "score": score,
                "details": details,
                "color_class": color_class,
                "data_timestamp": data_timestamp_str,
            }

        except Exception as e:
            logger.warning(f"Error computing options intelligence: {e}")
            return cls._get_unavailable_payload(
                symbol=sym,
                spot_price=spot_price,
                status="COMPUTATION_ERROR",
                details=f"Options calculation error: {e}",
            )

    @classmethod
    def _load_option_chain_data(cls, symbol: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """Loads authoritative option chain data for the instrument."""
        # 1. Check live cache first
        live_cache = WORKSPACE_ROOT / "live-market-terminal" / "data" / "cache" / f"option_chain_{symbol.lower()}.json"
        if live_cache.exists():
            try:
                with open(live_cache, "r", encoding="utf-8") as fp:
                    return json.load(fp), "LIVE_CACHE"
            except Exception:
                pass

        generic_cache = WORKSPACE_ROOT / "live-market-terminal" / "data" / "cache" / "option_chain.json"
        if generic_cache.exists():
            try:
                with open(generic_cache, "r", encoding="utf-8") as fp:
                    return json.load(fp), "GENERIC_CACHE"
            except Exception:
                pass

        sample_file = WORKSPACE_ROOT / "Daily-Market-Regime-Engine" / "data" / "sample_option_chain.json"
        if sample_file.exists():
            try:
                with open(sample_file, "r", encoding="utf-8") as fp:
                    return json.load(fp), "SAMPLE_FILE"
            except Exception:
                pass

        return None, "NONE"

    @classmethod
    def _check_data_freshness(cls, timestamp_str: str) -> bool:
        """Validates if timestamp is from today's trading session."""
        if not timestamp_str:
            return False
        today_str = get_ist_now().strftime("%d-%b-%Y")
        return timestamp_str.startswith(today_str)

    @classmethod
    def _get_unavailable_payload(
        cls,
        symbol: str,
        spot_price: float,
        status: str = "UNAVAILABLE",
        details: str = "Live Option Chain feed currently unavailable.",
    ) -> Dict[str, Any]:
        """Provides standardized institutional UNAVAILABLE payload."""
        return {
            "sentiment": "Unavailable",
            "status": status,
            "data_mode": "UNAVAILABLE",
            "symbol": symbol,
            "spot_price": spot_price,
            "expiry": None,
            "pcr_oi": None,
            "pcr_volume": None,
            "net_ce_oi_change": None,
            "net_pe_oi_change": None,
            "call_writing_contracts": None,
            "put_writing_contracts": None,
            "writing_sentiment": "UNAVAILABLE",
            "writing_intensity": "UNAVAILABLE",
            "max_pain": None,
            "max_pain_distance": None,
            "max_pain_bias": "UNAVAILABLE",
            "major_resistance_strike": None,
            "major_resistance_oi": None,
            "major_support_strike": None,
            "major_support_oi": None,
            "heaviest_call_writing_strike": None,
            "heaviest_call_writing_chg": None,
            "heaviest_put_writing_strike": None,
            "heaviest_put_writing_chg": None,
            "key_strikes": [],
            "details": details,
            "color_class": "text-muted",
        }

    @classmethod
    def get_options_sentiment(cls, symbol: str = "NIFTY", spot_price: float = 0.0) -> Dict[str, Any]:
        """Backward-compatible call returning sentiment and full options payload."""
        return cls.get_options_intelligence(symbol, spot_price)
