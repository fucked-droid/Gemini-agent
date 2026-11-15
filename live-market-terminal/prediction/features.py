"""
Feature Engineering for Predictive Directional Models.
Extracts past-only features with strict zero-future-leakage guarantees.
"""

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger("FeatureEngineer")

class FeatureEngineer:
    """
    Extracts time-series features strictly from historical/past data.
    """

    @classmethod
    def extract_features(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Builds feature matrix from enriched OHLCV candle DataFrame.
        """
        if df.empty or len(df) < 15:
            return pd.DataFrame()

        df_feat = pd.DataFrame(index=df.index)

        # 1. Log returns over multiple lookbacks (lagged, strictly past)
        close = df["Close"].astype(float)
        df_feat["ret_1"] = np.log(close / close.shift(1))
        df_feat["ret_3"] = np.log(close / close.shift(3))
        df_feat["ret_5"] = np.log(close / close.shift(5))

        # 2. Distances to Moving Averages & VWAP
        if "EMA10" in df.columns:
            df_feat["dist_ema10"] = (close - df["EMA10"]) / df["EMA10"]
        if "EMA20" in df.columns:
            df_feat["dist_ema20"] = (close - df["EMA20"]) / df["EMA20"]
        if "VWAP" in df.columns:
            df_feat["dist_vwap"] = (close - df["VWAP"]) / df["VWAP"]

        # 3. Momentum Dynamics
        if "RSI" in df.columns:
            df_feat["rsi"] = df["RSI"]
            df_feat["rsi_slope"] = df["RSI"] - df["RSI"].shift(3)
        if "MACD_Hist" in df.columns:
            df_feat["macd_hist"] = df["MACD_Hist"]
            df_feat["macd_accel"] = df["MACD_Hist"] - df["MACD_Hist"].shift(1)

        # 4. Volatility Normalization
        if "ATR" in df.columns:
            atr = df["ATR"].replace(0, np.nan)
            df_feat["norm_ret_1"] = (close - close.shift(1)) / atr

        # 5. Volume Intensity
        if "Volume" in df.columns:
            vol = df["Volume"].astype(float)
            vol_ma = vol.rolling(10).mean().replace(0, np.nan)
            df_feat["vol_ratio"] = vol / vol_ma

        # Clean NaN rows created by rolling windows
        return df_feat.dropna()
