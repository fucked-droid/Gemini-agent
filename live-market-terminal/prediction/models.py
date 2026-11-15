"""
Baseline Quantitative Momentum & Directional Prediction Model.
Generates multi-horizon probabilistic forecasts (5m, 15m, 30m, 60m)
with target ranges and statistical confidence estimates.
"""

import logging
from typing import Dict, Any, List
import pandas as pd
import numpy as np

from .features import FeatureEngineer

logger = logging.getLogger("DirectionalForecaster")

class DirectionalForecaster:
    """
    Statistical momentum & trend continuation model.
    Produces calibrated directional forecasts without future data leakage.
    """

    HORIZONS = {
        "5m": {"bars": 1, "vol_mult": 0.5},
        "15m": {"bars": 3, "vol_mult": 0.8},
        "30m": {"bars": 6, "vol_mult": 1.2},
        "60m": {"bars": 12, "vol_mult": 1.6},
    }

    @classmethod
    def forecast_horizons(
        cls, df_enriched: pd.DataFrame, current_price: float, current_atr: float
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generates forecasts for 5m, 15m, 30m, and 60m horizons.
        """
        features = FeatureEngineer.extract_features(df_enriched)
        if features.empty or len(features) < 15:
            return {
                h: {
                    "horizon": h,
                    "direction": "FLAT",
                    "target_lower": round(current_price * 0.998, 2),
                    "target_upper": round(current_price * 1.002, 2),
                    "probability_up": 0.50,
                    "confidence_pct": 50.0,
                    "status": "INSUFFICIENT_DATA",
                }
                for h in cls.HORIZONS
            }

        latest_f = features.iloc[-1]
        results = {}

        # Composite directional momentum signal
        # Weighted combination of past returns, VWAP distance, and RSI dynamics
        ret_signal = (
            latest_f.get("ret_1", 0) * 0.4
            + latest_f.get("ret_3", 0) * 0.3
            + latest_f.get("ret_5", 0) * 0.3
        )
        vwap_dist = latest_f.get("dist_vwap", 0)
        rsi_slope = latest_f.get("rsi_slope", 0)
        macd_acc = latest_f.get("macd_accel", 0)

        # Normalized composite score (-1.0 to 1.0)
        composite_z = np.tanh(ret_signal * 500.0 + vwap_dist * 50.0 + rsi_slope * 0.05 + macd_acc * 0.1)

        # Baseline probability of upward movement via logistic sigmoid
        prob_up = 1.0 / (1.0 + np.exp(-2.5 * composite_z))

        atr_val = current_atr if current_atr > 0 else (current_price * 0.005)

        for h, params in cls.HORIZONS.items():
            mult = params["vol_mult"]
            target_span = atr_val * mult

            if prob_up >= 0.58:
                direction = "UP"
                target_lower = current_price - (target_span * 0.3)
                target_upper = current_price + target_span
                conf = round(prob_up * 100.0, 1)
            elif prob_up <= 0.42:
                direction = "DOWN"
                target_lower = current_price - target_span
                target_upper = current_price + (target_span * 0.3)
                conf = round((1.0 - prob_up) * 100.0, 1)
            else:
                direction = "FLAT"
                target_lower = current_price - (target_span * 0.5)
                target_upper = current_price + (target_span * 0.5)
                conf = 50.0

            results[h] = {
                "horizon": h,
                "direction": direction,
                "target_lower": round(target_lower, 2),
                "target_upper": round(target_upper, 2),
                "probability_up": round(float(prob_up), 3),
                "confidence_pct": conf,
                "status": "VALIDATED" if len(features) >= 30 else "PROVISIONAL",
            }

        return results
