"""
Order Flow & Cumulative Volume Delta (CVD) Analytics Engine.
Calculates bar-level volume delta decomposition, cumulative session delta (CVD),
buyer vs seller pressure ratio, absorption divergence patterns,
session Volume Profile (POC, VAH, VAL), and multi-band VWAP volatility channels.
"""

import math
import logging
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger("OrderFlowAnalyzer")

class OrderFlowAnalyzer:
    """
    Implements institutional order flow metrics:
    - Intra-candle Volume Delta Decomposition (Lee-Ready / Wick-body methodology)
    - Cumulative Volume Delta (CVD)
    - Buying vs Selling Pressure percentages & Aggression ratio
    - Volume Absorption and Delta Divergence
    - Session Volume Profile (POC, VAH 70%, VAL 70%, Price Distribution Bins)
    - Anchored VWAP with Standard Deviation Volatility Bands (±1σ, ±2σ)
    """

    @staticmethod
    def compute_volume_delta(df: pd.DataFrame) -> pd.DataFrame:
        """
        Decomposes total bar volume into estimated Buy Volume and Sell Volume.
        Formula:
          Price Range = High - Low
          If Range == 0: Buy Vol = Sell Vol = Total Vol / 2
          Else:
            Buyer Ratio = (Close - Low) / Range
            Buy Vol = Volume * Buyer Ratio
            Sell Vol = Volume * (1 - Buyer Ratio)
            Bar Delta = Buy Vol - Sell Vol
            CVD = cumsum(Bar Delta)
        """
        if df.empty or "Volume" not in df.columns:
            df["Buy_Volume"] = 0
            df["Sell_Volume"] = 0
            df["Delta"] = 0
            df["CVD"] = 0
            return df

        df = df.copy()
        high = df["High"].astype(float)
        low = df["Low"].astype(float)
        close = df["Close"].astype(float)
        vol = df["Volume"].astype(float)

        bar_range = (high - low).replace(0, np.nan)
        buyer_ratio = ((close - low) / bar_range).clip(lower=0.0, upper=1.0)
        # For dojis or zero range, assign 50/50
        buyer_ratio = buyer_ratio.fillna(0.5)

        buy_vol = vol * buyer_ratio
        sell_vol = vol * (1.0 - buyer_ratio)
        delta = buy_vol - sell_vol

        df["Buy_Volume"] = buy_vol.round().astype(int)
        df["Sell_Volume"] = sell_vol.round().astype(int)
        df["Delta"] = delta.round().astype(int)
        df["CVD"] = df["Delta"].cumsum()

        return df

    @classmethod
    def compute_volume_profile(
        cls,
        df: pd.DataFrame,
        n_bins: int = 15,
        value_area_pct: float = 0.70,
    ) -> Dict[str, Any]:
        """
        Constructs horizontal Volume Profile histogram across session price levels:
        1. Point of Control (POC): Price bin with the highest traded volume.
        2. Value Area High (VAH) & Value Area Low (VAL): 70% volume boundaries expanding from POC.
        3. Value Area Position: INSIDE_VALUE_AREA, ABOVE_VAH, BELOW_VAL, or AT_POC.
        4. Bins array with relative volume weights for front-end rendering.
        """
        if df.empty or len(df) < 3 or "Volume" not in df.columns:
            last_close = float(df["Close"].iloc[-1]) if not df.empty and "Close" in df.columns else 24500.0
            return {
                "poc": last_close,
                "vah": last_close + 50.0,
                "val": last_close - 50.0,
                "value_area_span": 100.0,
                "position": "INSIDE_VALUE_AREA",
                "position_label": "Inside Value Area (Fair Value Equilibrium)",
                "total_volume": 0,
                "bins": [],
            }

        df_flow = cls.compute_volume_delta(df)
        min_p = float(df_flow["Low"].min())
        max_p = float(df_flow["High"].max())
        current_p = float(df_flow["Close"].iloc[-1])

        if max_p <= min_p:
            max_p = min_p + 10.0

        bin_step = (max_p - min_p) / n_bins
        # Setup bin boundaries
        bin_edges = [min_p + (i * bin_step) for i in range(n_bins + 1)]
        bin_mids = [(bin_edges[i] + bin_edges[i + 1]) / 2.0 for i in range(n_bins)]
        bin_vols = [0.0] * n_bins
        bin_buy_vols = [0.0] * n_bins
        bin_sell_vols = [0.0] * n_bins

        total_vol = 0.0

        for _, row in df_flow.iterrows():
            h = float(row["High"])
            l = float(row["Low"])
            v = float(row["Volume"])
            b_v = float(row["Buy_Volume"])
            s_v = float(row["Sell_Volume"])

            if v <= 0:
                continue
            total_vol += v

            # Find overlapping bins
            spanned_indices = [
                i for i in range(n_bins)
                if not (h < bin_edges[i] or l > bin_edges[i + 1])
            ]

            if spanned_indices:
                alloc_vol = v / len(spanned_indices)
                alloc_buy = b_v / len(spanned_indices)
                alloc_sell = s_v / len(spanned_indices)
                for idx in spanned_indices:
                    bin_vols[idx] += alloc_vol
                    bin_buy_vols[idx] += alloc_buy
                    bin_sell_vols[idx] += alloc_sell
            else:
                # Fallback to closest mid
                closest_idx = min(range(n_bins), key=lambda i: abs(bin_mids[i] - l))
                bin_vols[closest_idx] += v
                bin_buy_vols[closest_idx] += b_v
                bin_sell_vols[closest_idx] += s_v

        # Point of Control (POC): bin index with highest volume
        poc_idx = int(np.argmax(bin_vols))
        poc_price = round(bin_mids[poc_idx], 2)
        max_bin_vol = bin_vols[poc_idx] if bin_vols[poc_idx] > 0 else 1.0

        # Calculate 70% Value Area starting from POC and expanding to higher neighbor
        target_va_vol = total_vol * value_area_pct
        accumulated_vol = bin_vols[poc_idx]
        va_indices = {poc_idx}

        up_idx = poc_idx + 1
        dn_idx = poc_idx - 1

        while accumulated_vol < target_va_vol and (up_idx < n_bins or dn_idx >= 0):
            up_vol = bin_vols[up_idx] if up_idx < n_bins else -1.0
            dn_vol = bin_vols[dn_idx] if dn_idx >= 0 else -1.0

            if up_vol >= dn_vol and up_vol >= 0:
                accumulated_vol += up_vol
                va_indices.add(up_idx)
                up_idx += 1
            elif dn_vol >= 0:
                accumulated_vol += dn_vol
                va_indices.add(dn_idx)
                dn_idx -= 1
            else:
                break

        vah_idx = max(va_indices)
        val_idx = min(va_indices)
        vah_price = round(bin_edges[vah_idx + 1], 2)
        val_price = round(bin_edges[val_idx], 2)

        # Position evaluation
        if current_p > vah_price:
            position = "ABOVE_VAH"
            position_label = f"Above VAH (₹{vah_price:,.0f}) — Initiative Buying Auction"
        elif current_p < val_price:
            position = "BELOW_VAL"
            position_label = f"Below VAL (₹{val_price:,.0f}) — Initiative Selling Auction"
        elif abs(current_p - poc_price) <= (bin_step * 0.75):
            position = "AT_POC"
            position_label = f"At POC (₹{poc_price:,.0f}) — High Volume Equilibrium"
        else:
            position = "INSIDE_VALUE_AREA"
            position_label = f"Inside Value Area [₹{val_price:,.0f} - ₹{vah_price:,.0f}] — Two-Way Responsive Flow"

        # Construct serializable bin objects for UI bar charts
        bins_data: List[Dict[str, Any]] = []
        for i in range(n_bins):
            v = bin_vols[i]
            bv = bin_buy_vols[i]
            sv = bin_sell_vols[i]
            pct = round((v / max_bin_vol) * 100.0, 1) if max_bin_vol > 0 else 0.0
            is_in_va = (i in va_indices)
            bins_data.append({
                "price": round(bin_mids[i], 2),
                "volume": int(v),
                "buy_volume": int(bv),
                "sell_volume": int(sv),
                "pct_of_max": pct,
                "is_poc": (i == poc_idx),
                "in_value_area": is_in_va,
            })

        return {
            "poc": poc_price,
            "vah": vah_price,
            "val": val_price,
            "value_area_span": round(vah_price - val_price, 2),
            "position": position,
            "position_label": position_label,
            "total_volume": int(total_vol),
            "bins": bins_data,
        }

    @classmethod
    def compute_vwap_bands(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates session VWAP and Standard Deviation Bands (±1σ, ±2σ).
        """
        if df.empty or "Volume" not in df.columns:
            return {
                "vwap": 0.0,
                "upper_1sigma": 0.0,
                "upper_2sigma": 0.0,
                "lower_1sigma": 0.0,
                "lower_2sigma": 0.0,
                "position": "AT_VWAP",
                "position_label": "At VWAP",
                "deviation_pts": 0.0,
            }

        high = df["High"].astype(float)
        low = df["Low"].astype(float)
        close = df["Close"].astype(float)
        vol = df["Volume"].astype(float)

        tp = (high + low + close) / 3.0
        cum_vol = vol.cumsum().replace(0, 1.0)
        vwap_series = (tp * vol).cumsum() / cum_vol
        vwap_val = round(float(vwap_series.iloc[-1]), 2)

        # Standard Deviation of Price from VWAP weighted by Volume
        sq_diff = (tp - vwap_series) ** 2
        variance = (sq_diff * vol).cumsum() / cum_vol
        std_val = float(np.sqrt(variance.iloc[-1]))
        std_val = max(std_val, vwap_val * 0.001)  # Safeguard minimum std

        upper_1s = round(vwap_val + std_val, 2)
        upper_2s = round(vwap_val + (2.0 * std_val), 2)
        lower_1s = round(vwap_val - std_val, 2)
        lower_2s = round(vwap_val - (2.0 * std_val), 2)

        current_p = float(close.iloc[-1])
        dev_pts = round(current_p - vwap_val, 2)

        if current_p > upper_2s:
            pos = "ABOVE_UPPER_2SIGMA"
            pos_label = f"Overbought (+2σ at ₹{upper_2s:,.0f}) — Mean Reversion Risk"
        elif current_p > upper_1s:
            pos = "ABOVE_UPPER_1SIGMA"
            pos_label = f"Bullish Expansion (+1σ at ₹{upper_1s:,.0f}) — Buyers in Control"
        elif current_p < lower_2s:
            pos = "BELOW_LOWER_2SIGMA"
            pos_label = f"Oversold (-2σ at ₹{lower_2s:,.0f}) — Short Exhaustion Risk"
        elif current_p < lower_1s:
            pos = "BELOW_LOWER_1SIGMA"
            pos_label = f"Bearish Expansion (-1σ at ₹{lower_1s:,.0f}) — Sellers in Control"
        else:
            pos = "AT_VWAP"
            pos_label = f"At Session VWAP (₹{vwap_val:,.0f}) — Central Value Equilibrium"

        return {
            "vwap": vwap_val,
            "upper_1sigma": upper_1s,
            "upper_2sigma": upper_2s,
            "lower_1sigma": lower_1s,
            "lower_2sigma": lower_2s,
            "position": pos,
            "position_label": pos_label,
            "deviation_pts": dev_pts,
        }

    @classmethod
    def analyze_order_flow(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Extracts comprehensive institutional order flow conditions:
        - Volume Delta decomposition
        - Cumulative Volume Delta (CVD)
        - Buyer vs Seller Aggression ratio
        - Absorption / Exhaustion Divergence
        - Session Volume Profile
        - Multi-band VWAP volatility channels
        """
        if df.empty or len(df) < 5:
            return {
                "order_flow_state": "NEUTRAL",
                "cvd": 0,
                "buyer_percentage": 50.0,
                "seller_percentage": 50.0,
                "aggression_ratio": 1.0,
                "aggression_state": "Balanced Aggression",
                "volume_ratio": 1.0,
                "divergence": "NONE",
                "summary": "Insufficient candles for order flow analysis.",
                "volume_profile": {
                    "poc": 0.0,
                    "vah": 0.0,
                    "val": 0.0,
                    "value_area_span": 0.0,
                    "position": "INSIDE_VALUE_AREA",
                    "position_label": "Inside Value Area",
                    "total_volume": 0,
                    "bins": [],
                },
                "vwap_bands": {
                    "vwap": 0.0,
                    "upper_1sigma": 0.0,
                    "upper_2sigma": 0.0,
                    "lower_1sigma": 0.0,
                    "lower_2sigma": 0.0,
                    "position": "AT_VWAP",
                    "position_label": "At VWAP",
                    "deviation_pts": 0.0,
                },
            }

        df_flow = cls.compute_volume_delta(df)
        total_vol = df_flow["Volume"].sum()
        total_buy = df_flow["Buy_Volume"].sum()
        total_sell = df_flow["Sell_Volume"].sum()

        buyer_pct = (total_buy / total_vol * 100.0) if total_vol > 0 else 50.0
        seller_pct = 100.0 - buyer_pct
        current_cvd = int(df_flow["CVD"].iloc[-1])

        # Aggression Ratio (Buy Volume / Sell Volume)
        agg_ratio = round(total_buy / total_sell, 2) if total_sell > 0 else 1.0
        if agg_ratio >= 1.35:
            agg_state = "Aggressive Buyers Dominating Auction"
        elif agg_ratio <= 0.75:
            agg_state = "Aggressive Sellers Driving Auction"
        else:
            agg_state = "Balanced Two-Way Auction"

        # Volume ratio vs 20-period moving average
        recent_vol = df_flow["Volume"].iloc[-1]
        avg_vol = df_flow["Volume"].tail(20).mean()
        vol_ratio = round(recent_vol / avg_vol, 2) if avg_vol > 0 else 1.0

        # CVD Trend & Divergence over the last 10 bars
        last_10 = df_flow.tail(10)
        price_change = last_10["Close"].iloc[-1] - last_10["Close"].iloc[0]
        cvd_change = last_10["CVD"].iloc[-1] - last_10["CVD"].iloc[0]

        divergence = "NONE"
        if price_change > 0 and cvd_change < 0:
            divergence = "BEARISH_ABSORPTION_EXHAUSTION"  # Price higher, but selling delta
        elif price_change < 0 and cvd_change > 0:
            divergence = "BULLISH_ACCUMULATION_ABSORPTION"  # Price lower, but buying delta

        # Order flow state classification
        if buyer_pct >= 58.0 and cvd_change > 0:
            state = "STRONG_BULLISH_FLOW"
        elif buyer_pct > 52.0:
            state = "MODERATE_BULLISH_FLOW"
        elif seller_pct >= 58.0 and cvd_change < 0:
            state = "STRONG_BEARISH_FLOW"
        elif seller_pct > 52.0:
            state = "MODERATE_BEARISH_FLOW"
        else:
            state = "NEUTRAL_CHOP_FLOW"

        # Volume Profile calculation
        volume_profile = cls.compute_volume_profile(df_flow, n_bins=12, value_area_pct=0.70)

        # VWAP & Standard Deviation Bands
        vwap_bands = cls.compute_vwap_bands(df_flow)

        summary = (
            f"{state.replace('_', ' ')}: Buyers {buyer_pct:.1f}% vs Sellers {seller_pct:.1f}% (Aggression: {agg_ratio:.2f}x). "
            f"CVD: {current_cvd:+d} contracts. POC: ₹{volume_profile['poc']:,.0f} | VAH: ₹{volume_profile['vah']:,.0f} | VAL: ₹{volume_profile['val']:,.0f}. "
            f"Divergence: {divergence}."
        )

        return {
            "order_flow_state": state,
            "cvd": current_cvd,
            "buyer_percentage": round(buyer_pct, 1),
            "seller_percentage": round(seller_pct, 1),
            "total_buy_volume": int(total_buy),
            "total_sell_volume": int(total_sell),
            "aggression_ratio": agg_ratio,
            "aggression_state": agg_state,
            "volume_ratio": vol_ratio,
            "divergence": divergence,
            "volume_profile": volume_profile,
            "vwap_bands": vwap_bands,
            "summary": summary,
            "df_with_cvd": df_flow,
        }
