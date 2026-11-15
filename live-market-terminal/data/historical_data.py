"""
Historical Data & Multi-Timeframe Resampling Manager.
Prepares, validates, and aggregates raw minute bars into 5m, 15m, 30m, and 60m
OHLCV datasets with strict invariant guarantees.
"""

import logging
from typing import Dict
import pandas as pd
import numpy as np

logger = logging.getLogger("HistoricalDataManager")

class HistoricalDataManager:
    """
    Handles candle validation, timestamp alignment, and multi-timeframe aggregation.
    """

    @staticmethod
    def validate_ohlc(df: pd.DataFrame) -> pd.DataFrame:
        """
        Validates and fixes basic OHLC invariants:
        - High >= Low
        - High >= max(Open, Close)
        - Low <= min(Open, Close)
        - Volume >= 0
        """
        if df.empty:
            return df

        df = df.copy()
        # Ensure column casing
        rename_map = {c: c.capitalize() for c in df.columns if c.lower() in ["open", "high", "low", "close", "volume"]}
        df.rename(columns=rename_map, inplace=True)

        for col in ["Open", "High", "Low", "Close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["Volume"] = pd.to_numeric(df.get("Volume", 0), errors="coerce").fillna(0).astype(int)

        # Drop NaN closes
        df.dropna(subset=["Close"], inplace=True)
        if df.empty:
            return df

        # Invariant corrections
        df["High"] = np.maximum(df["High"], np.maximum(df["Open"], df["Close"]))
        df["Low"] = np.minimum(df["Low"], np.minimum(df["Open"], df["Close"]))
        df["Volume"] = np.maximum(df["Volume"], 0)

        return df

    @classmethod
    def resample_candles(cls, df_1m: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
        """
        Resamples 1-minute OHLCV data to target timeframe ('5m', '15m', '30m', '60m').
        """
        if df_1m.empty:
            return df_1m

        df = cls.validate_ohlc(df_1m)
        if not isinstance(df.index, pd.DatetimeIndex):
            if "Timestamp" in df.columns or "Datetime" in df.columns:
                col = "Timestamp" if "Timestamp" in df.columns else "Datetime"
                df[col] = pd.to_datetime(df[col])
                df.set_index(col, inplace=True)
            else:
                return df

        rule_map = {
            "1m": "1min",
            "3m": "3min",
            "5m": "5min",
            "15m": "15min",
            "30m": "30min",
            "60m": "60min",
            "1h": "60min",
        }
        rule = rule_map.get(target_timeframe.lower(), "5min")
        if rule == "1min":
            return df

        resampled = df.resample(rule, closed="left", label="left").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        }).dropna(subset=["Close"])

        return cls.validate_ohlc(resampled)

    @classmethod
    def build_timeframe_suite(cls, base_candles: pd.DataFrame, timeframes=None) -> Dict[str, pd.DataFrame]:
        """
        Given a base DataFrame of intraday candles, builds all supported timeframes.
        """
        if timeframes is None:
            timeframes = ["1m", "3m", "5m", "15m", "30m", "60m"]

        suite = {}
        for tf in timeframes:
            suite[tf] = cls.resample_candles(base_candles, tf)
        return suite
