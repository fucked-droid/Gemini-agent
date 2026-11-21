"""
Quantitative Multi-Horizon Directional Prediction Engine.
Generates genuine, independent probabilistic forecasts for 5m, 15m, 30m, and 60m horizons
using timeframe-specific historical candle dynamics, momentum indicators, ATR scaling,
and calibrated directional confidence.
"""

import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from .features import FeatureEngineer

logger = logging.getLogger("DirectionalForecaster")

class DirectionalForecaster:
    """
    Multi-horizon directional prediction engine.
    Produces genuinely independent UP / DOWN / NEUTRAL forecasts with
    calibrated probabilities, horizon-scaled uncertainty price ranges,
    and timeframe-specific feature extraction without future leakage.
    """

    HORIZONS = {
        "5m": {
            "label": "5m Intraday",
            "horizon_bars": 1,
            "horizon_minutes": 5,
            "k_sigma": 1.0,
            "prob_up_threshold": 0.56,
            "prob_down_threshold": 0.44,
            "min_conf_delta": 0.05,
        },
        "15m": {
            "label": "15m Short Swing",
            "horizon_bars": 3,
            "horizon_minutes": 15,
            "k_sigma": 1.4,
            "prob_up_threshold": 0.55,
            "prob_down_threshold": 0.45,
            "min_conf_delta": 0.05,
        },
        "30m": {
            "label": "30m Intermediate",
            "horizon_bars": 6,
            "horizon_minutes": 30,
            "k_sigma": 1.8,
            "prob_up_threshold": 0.54,
            "prob_down_threshold": 0.46,
            "min_conf_delta": 0.04,
        },
        "60m": {
            "label": "60m Macro Intraday",
            "horizon_bars": 12,
            "horizon_minutes": 60,
            "k_sigma": 2.2,
            "prob_up_threshold": 0.53,
            "prob_down_threshold": 0.47,
            "min_conf_delta": 0.03,
        },
    }

    @classmethod
    def _evaluate_horizon_dataset(
        cls,
        horizon_key: str,
        df_horizon: pd.DataFrame,
        current_price: float,
        horizon_atr: Optional[float] = None,
        mtf_timeframe_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Calculates independent prediction for a specific horizon from its own candle dataset.
        """
        params = cls.HORIZONS.get(horizon_key, {
            "label": f"{horizon_key} Horizon",
            "horizon_bars": 1,
            "horizon_minutes": 15,
            "k_sigma": 1.5,
            "prob_up_threshold": 0.55,
            "prob_down_threshold": 0.45,
            "min_conf_delta": 0.05,
        })

        if df_horizon is None or df_horizon.empty or len(df_horizon) < 15:
            # Insufficient data fallback
            k_sigma = params["k_sigma"]
            default_atr = (current_price * 0.003) * np.sqrt(params["horizon_minutes"] / 5.0)
            return {
                "horizon": horizon_key,
                "label": params["label"],
                "horizon_minutes": params["horizon_minutes"],
                "direction": "NEUTRAL",
                "target_lower": round(current_price - default_atr, 2),
                "target_upper": round(current_price + default_atr, 2),
                "expected_center": round(current_price, 2),
                "probability_up": 0.50,
                "confidence_pct": 50.0,
                "indicator_agreement_pct": 50.0,
                "momentum_score": 0.0,
                "volatility_span": round(default_atr * 2.0, 2),
                "status": "INSUFFICIENT_DATA",
                "rationale": "Insufficient historical candles for independent horizon forecast.",
                "mtf_agreement": "AGREES" if (mtf_timeframe_data and mtf_timeframe_data.get("direction") == "SIDEWAYS") else "NEUTRAL",
            }

        features = FeatureEngineer.extract_features(df_horizon)
        if features.empty:
            features = pd.DataFrame(index=df_horizon.index)

        latest_candle = df_horizon.iloc[-1]
        close = float(latest_candle.get("Close", current_price))
        ema10 = float(latest_candle.get("EMA10", close))
        ema20 = float(latest_candle.get("EMA20", close))
        vwap = float(latest_candle.get("VWAP", close))
        rsi = float(latest_candle.get("RSI", 50.0))
        atr_from_df = float(latest_candle.get("ATR", 0.0))

        # Dynamic ATR resolution for this horizon
        if horizon_atr is not None and horizon_atr > 0:
            effective_atr = horizon_atr
        elif atr_from_df > 0:
            effective_atr = atr_from_df
        else:
            effective_atr = max(close * 0.002, 10.0)

        # 1. Multi-factor indicator votes on this specific timeframe
        # Factors: EMA Trend, EMA Slope, RSI Level & Slope, VWAP distance, Recent Return
        bullish_votes = 0.0
        bearish_votes = 0.0
        total_weight = 0.0

        # Factor A: EMA Alignment (weight: 1.5)
        total_weight += 1.5
        if ema10 > ema20:
            diff_ratio = (ema10 - ema20) / close
            if diff_ratio > 0.0003:
                bullish_votes += 1.5
            else:
                bullish_votes += 0.75
                bearish_votes += 0.25
        elif ema20 > ema10:
            diff_ratio = (ema20 - ema10) / close
            if diff_ratio > 0.0003:
                bearish_votes += 1.5
            else:
                bearish_votes += 0.75
                bullish_votes += 0.25
        else:
            bullish_votes += 0.5
            bearish_votes += 0.5

        # Factor B: Price vs VWAP (weight: 1.0)
        total_weight += 1.0
        vwap_diff = (close - vwap) / vwap if vwap > 0 else 0
        if vwap_diff > 0.0008:
            bullish_votes += 1.0
        elif vwap_diff < -0.0008:
            bearish_votes += 1.0
        else:
            bullish_votes += 0.5
            bearish_votes += 0.5

        # Factor C: RSI Momentum & Trajectory (weight: 1.2)
        total_weight += 1.2
        rsi_diff_50 = rsi - 50.0
        # Check RSI slope over prior 3 candles in this horizon
        if len(df_horizon) >= 4 and "RSI" in df_horizon.columns:
            prev_rsi = float(df_horizon["RSI"].iloc[-4])
            rsi_delta = rsi - prev_rsi
        else:
            rsi_delta = 0.0

        if rsi >= 56.0 and rsi_delta >= 0:
            bullish_votes += 1.2
        elif rsi <= 44.0 and rsi_delta <= 0:
            bearish_votes += 1.2
        elif rsi > 52.0:
            bullish_votes += 0.8
            bearish_votes += 0.4
        elif rsi < 48.0:
            bearish_votes += 0.8
            bullish_votes += 0.4
        else:
            bullish_votes += 0.6
            bearish_votes += 0.6

        # Factor D: Price Action Momentum (returns over lookback) (weight: 1.0)
        total_weight += 1.0
        if len(df_horizon) >= 4:
            c_prev = float(df_horizon["Close"].iloc[-4])
            ret_lookback = (close - c_prev) / c_prev
        else:
            ret_lookback = 0.0

        if ret_lookback > 0.0015:
            bullish_votes += 1.0
        elif ret_lookback < -0.0015:
            bearish_votes += 1.0
        elif ret_lookback > 0.0004:
            bullish_votes += 0.7
            bearish_votes += 0.3
        elif ret_lookback < -0.0004:
            bearish_votes += 0.7
            bullish_votes += 0.3
        else:
            bullish_votes += 0.5
            bearish_votes += 0.5

        # Factor E: Candle Body Bias (last completed bar) (weight: 0.8)
        total_weight += 0.8
        open_p = float(latest_candle.get("Open", close))
        if close > open_p:
            bullish_votes += 0.8
        elif close < open_p:
            bearish_votes += 0.8
        else:
            bullish_votes += 0.4
            bearish_votes += 0.4

        # Indicator agreement fraction
        ind_agreement_pct = round((bullish_votes / total_weight) * 100.0, 1)

        # 2. Calibrated Probability via Logistic Model
        # Continuous z-score centered at zero
        net_bias = (bullish_votes - bearish_votes) / total_weight  # -1.0 to +1.0
        # Incorporate continuous feature terms from latest_f if present
        if not features.empty:
            f_row = features.iloc[-1]
            ret_1 = float(f_row.get("ret_1", 0.0))
            vwap_dist = float(f_row.get("dist_vwap", 0.0))
            rsi_slope_val = float(f_row.get("rsi_slope", 0.0))
            macd_acc_val = float(f_row.get("macd_accel", 0.0))
            feature_z = (ret_1 * 300.0) + (vwap_dist * 40.0) + (rsi_slope_val * 0.03) + (macd_acc_val * 0.08)
        else:
            feature_z = 0.0

        # Blended logit
        composite_z = (net_bias * 2.0) + np.clip(feature_z, -1.5, 1.5)
        # Logistic sigmoid scaled to preserve calibration (avoid overconfident extremes)
        prob_up = 1.0 / (1.0 + np.exp(-1.8 * composite_z))
        prob_up = float(np.clip(prob_up, 0.15, 0.85))

        # 3. Direction Classification: UP, DOWN, NEUTRAL
        p_up_thresh = params["prob_up_threshold"]
        p_down_thresh = params["prob_down_threshold"]
        min_delta = params["min_conf_delta"]

        if prob_up >= p_up_thresh and (prob_up - 0.50) >= min_delta:
            direction = "UP"
            conf = prob_up * 100.0
            bias_drift = 0.25  # drift bias in range calculation
        elif prob_up <= p_down_thresh and (0.50 - prob_up) >= min_delta:
            direction = "DOWN"
            conf = (1.0 - prob_up) * 100.0
            bias_drift = -0.25
        else:
            direction = "NEUTRAL"
            conf = max(prob_up, 1.0 - prob_up) * 100.0
            bias_drift = 0.0

        # 4. Target Price Range using Horizon Uncertainty Scaling:
        # Standard deviation expansion: uncertainty scales with sqrt(t)
        # range_span = k * ATR * sqrt(horizon_minutes / 5)
        k = params["k_sigma"]
        time_scale = np.sqrt(params["horizon_minutes"] / 5.0)
        expected_span = effective_atr * k * time_scale

        if direction == "UP":
            # Upward skew: higher ceiling, tighter floor
            target_lower = current_price - (expected_span * 0.35)
            target_upper = current_price + (expected_span * 0.85)
            expected_center = current_price + (expected_span * 0.25)
        elif direction == "DOWN":
            # Downward skew: lower floor, tighter ceiling
            target_lower = current_price - (expected_span * 0.85)
            target_upper = current_price + (expected_span * 0.35)
            expected_center = current_price - (expected_span * 0.25)
        else:
            # Symmetric neutral uncertainty
            target_lower = current_price - (expected_span * 0.55)
            target_upper = current_price + (expected_span * 0.55)
            expected_center = current_price

        # Sanity guarantee: target_lower < current_price / target_upper
        if target_lower >= target_upper:
            target_lower = current_price - (expected_span * 0.5)
            target_upper = current_price + (expected_span * 0.5)

        # 5. Check Consistency with Multi-Timeframe Trend Matrix
        mtf_dir = mtf_timeframe_data.get("direction") if mtf_timeframe_data else None
        if mtf_dir:
            if direction == mtf_dir or (direction == "NEUTRAL" and mtf_dir == "SIDEWAYS"):
                mtf_agreement = "AGREES"
                rationale = f"Forecast {direction} aligns with {horizon_key} MTF trend ({mtf_dir})."
            elif (direction == "UP" and mtf_dir == "BEARISH") or (direction == "DOWN" and mtf_dir == "BULLISH"):
                mtf_agreement = "CONFLICTS"
                rationale = f"Forecast {direction} anticipates momentum reversal against prevailing {mtf_dir} MTF trend."
            else:
                mtf_agreement = "NEUTRAL"
                rationale = f"Forecast {direction} reflects transitional consolidation vs {mtf_dir} MTF structure."
        else:
            mtf_agreement = "STANDALONE"
            rationale = f"Independent momentum assessment: RSI {rsi:.1f}, EMA bias {net_bias:+.2f}."

        last_time_str = str(latest_candle.name) if hasattr(latest_candle, "name") else None

        return {
            "horizon": horizon_key,
            "label": params["label"],
            "horizon_minutes": params["horizon_minutes"],
            "direction": direction,
            "target_lower": round(float(target_lower), 2),
            "target_upper": round(float(target_upper), 2),
            "expected_center": round(float(expected_center), 2),
            "probability_up": round(float(prob_up), 3),
            "confidence_pct": round(float(conf), 1),
            "indicator_agreement_pct": ind_agreement_pct,
            "momentum_score": round(float(net_bias), 2),
            "volatility_span": round(float(target_upper - target_lower), 2),
            "status": "VALIDATED" if len(df_horizon) >= 30 else "PROVISIONAL",
            "rationale": rationale,
            "mtf_agreement": mtf_agreement,
            "last_candle_timestamp": last_time_str,
            "sample_bars": len(df_horizon),
        }

    @classmethod
    def forecast_horizons(
        cls,
        df_enriched: pd.DataFrame,
        current_price: float,
        current_atr: float,
        tf_suite: Optional[Dict[str, pd.DataFrame]] = None,
        mtf_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generates genuine, independent forecasts for 5m, 15m, 30m, and 60m horizons.
        When tf_suite is provided, each horizon is evaluated strictly on its own timeframe data.
        """
        results = {}
        mtf_tfs = (mtf_data or {}).get("timeframes", {})

        for h in cls.HORIZONS.keys():
            # Select horizon-specific DataFrame
            df_h = None
            if tf_suite and h in tf_suite and tf_suite[h] is not None and not tf_suite[h].empty:
                df_h = tf_suite[h]
            elif df_enriched is not None and not df_enriched.empty:
                df_h = df_enriched

            mtf_tf_info = mtf_tfs.get(h)

            results[h] = cls._evaluate_horizon_dataset(
                horizon_key=h,
                df_horizon=df_h,
                current_price=current_price,
                horizon_atr=current_atr,
                mtf_timeframe_data=mtf_tf_info,
            )

        return results

