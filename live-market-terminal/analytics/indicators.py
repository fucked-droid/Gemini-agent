"""
Technical Indicators Engine.
Vectorized calculations for EMA 10, EMA 20, VWAP, RSI, MACD, ATR,
Bollinger Bands, and Opening Range Breakout.
"""

import logging
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger("TechnicalIndicators")

class TechnicalIndicators:
    """
    Mathematical indicator implementations with strict null and zero-volume safety.
    """

    @staticmethod
    def compute_ema(series: pd.Series, period: int = 20) -> pd.Series:
        """Calculates Exponential Moving Average."""
        if series.empty or len(series) < period:
            return pd.Series(np.nan, index=series.index)
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def compute_vwap(df: pd.DataFrame) -> pd.Series:
        """
        Calculates intraday Volume Weighted Average Price (VWAP).
        Formula: Cumulative(Typical Price * Volume) / Cumulative(Volume)
        where Typical Price = (High + Low + Close) / 3.
        """
        if df.empty or "Volume" not in df.columns:
            return pd.Series(np.nan, index=df.index)

        typical_price = (df["High"] + df["Low"] + df["Close"]) / 3.0
        pv = typical_price * df["Volume"]

        # If DatetimeIndex spans multiple days, reset cumsum at day boundaries
        if isinstance(df.index, pd.DatetimeIndex) and len(df.index.normalize().unique()) > 1:
            cum_pv = pv.groupby(df.index.date).cumsum()
            cum_vol = df["Volume"].groupby(df.index.date).cumsum()
        else:
            cum_pv = pv.cumsum()
            cum_vol = df["Volume"].cumsum()

        # Handle zero-volume edge case (fallback to typical price if zero volume everywhere)
        vwap = cum_pv / cum_vol.replace(0, np.nan)
        return vwap.ffill().bfill().fillna(typical_price)

    @staticmethod
    def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculates Wilder's Smoothed Relative Strength Index (RSI).
        """
        if series.empty or len(series) <= period:
            return pd.Series(np.nan, index=series.index)

        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        # When loss is 0 and gain > 0, RSI is 100
        rsi = rsi.where(~((avg_loss == 0) & (avg_gain > 0)), 100.0)
        # When gain is 0 and loss > 0, RSI is 0
        rsi = rsi.where(~((avg_gain == 0) & (avg_loss > 0)), 0.0)
        rsi = rsi.fillna(50.0)
        return rsi

    @staticmethod
    def compute_macd(
        series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculates MACD Line, Signal Line, and MACD Histogram.
        """
        if series.empty or len(series) < slow:
            nan_s = pd.Series(np.nan, index=series.index)
            return nan_s, nan_s, nan_s

        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    @staticmethod
    def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculates Average True Range (ATR).
        TR = max(High - Low, |High - PrevClose|, |Low - PrevClose|)
        """
        if df.empty or len(df) < 2:
            return pd.Series(np.nan, index=df.index)

        high = df["High"]
        low = df["Low"]
        prev_close = df["Close"].shift(1)

        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = true_range.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
        return atr

    @staticmethod
    def compute_adx(df: pd.DataFrame, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculates Welles Wilder's Average Directional Index (ADX), +DI, and -DI.
        """
        if df.empty or len(df) < period + 1:
            nan_s = pd.Series(np.nan, index=df.index)
            return nan_s, nan_s, nan_s

        high = df["High"].astype(float)
        low = df["Low"].astype(float)
        close = df["Close"].astype(float)

        up_move = high.diff()
        down_move = -low.diff()

        pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        neg_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        tr = np.maximum(high - low, np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))))
        tr_s = pd.Series(tr, index=df.index).ewm(alpha=1.0 / period, adjust=False).mean()

        pos_di = 100.0 * (pd.Series(pos_dm, index=df.index).ewm(alpha=1.0 / period, adjust=False).mean() / tr_s.replace(0, np.nan)).fillna(0.0)
        neg_di = 100.0 * (pd.Series(neg_dm, index=df.index).ewm(alpha=1.0 / period, adjust=False).mean() / tr_s.replace(0, np.nan)).fillna(0.0)

        dx = 100.0 * (abs(pos_di - neg_di) / (pos_di + neg_di).replace(0, np.nan)).fillna(0.0)
        adx = dx.ewm(alpha=1.0 / period, adjust=False).mean()

        return adx, pos_di, neg_di

    @staticmethod
    def compute_bollinger_bands(
        series: pd.Series, period: int = 20, std_dev: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        """
        Calculates Upper Band, Middle Band, Lower Band, and %B.
        """
        if series.empty or len(series) < period:
            nan_s = pd.Series(np.nan, index=series.index)
            return nan_s, nan_s, nan_s, nan_s

        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)

        bandwidth = upper - lower
        pct_b = (series - lower) / bandwidth.replace(0, np.nan)

        return upper, middle, lower, pct_b

    @staticmethod
    def compute_opening_range(df: pd.DataFrame, minutes: int = 15) -> Dict[str, Any]:
        """
        Extracts opening range high/low for the first N minutes of the session
        and determines current breakout state.
        """
        if df.empty:
            return {"or_high": 0.0, "or_low": 0.0, "status": "UNKNOWN"}

        # First N bars assuming intraday sequence
        # Typically 15 min is 3 bars on 5m, or 15 bars on 1m
        or_df = df.iloc[:3] if len(df) >= 3 else df
        or_high = float(or_df["High"].max())
        or_low = float(or_df["Low"].min())
        current_price = float(df["Close"].iloc[-1])

        if current_price > or_high:
            status = "BULLISH_BREAKOUT_ABOVE_ORH"
        elif current_price < or_low:
            status = "BEARISH_BREAKDOWN_BELOW_ORL"
        else:
            status = "INSIDE_OPENING_RANGE"

        return {
            "or_high": round(or_high, 2),
            "or_low": round(or_low, 2),
            "current_price": round(current_price, 2),
            "status": status,
        }

    @classmethod
    def calculate_all(cls, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Enriches candle dataframe with all standard indicators and returns
        summary metrics of the latest bar.
        """
        if df.empty:
            return df, {}

        res = df.copy()
        res["EMA10"] = cls.compute_ema(res["Close"], 10)
        res["EMA20"] = cls.compute_ema(res["Close"], 20)
        res["VWAP"] = cls.compute_vwap(res)
        res["RSI"] = cls.compute_rsi(res["Close"], 14)

        macd, macd_sig, macd_hist = cls.compute_macd(res["Close"])
        res["MACD"] = macd
        res["MACD_Signal"] = macd_sig
        res["MACD_Hist"] = macd_hist

        res["ATR"] = cls.compute_atr(res, 14)
        bb_upper, bb_mid, bb_lower, pct_b = cls.compute_bollinger_bands(res["Close"])
        res["BB_Upper"] = bb_upper
        res["BB_Middle"] = bb_mid
        res["BB_Lower"] = bb_lower
        res["BB_PctB"] = pct_b

        latest = res.iloc[-1]
        or_data = cls.compute_opening_range(res, 15)

        scalars = {
            "close": float(latest["Close"]),
            "ema10": float(latest["EMA10"]) if not np.isnan(latest["EMA10"]) else latest["Close"],
            "ema20": float(latest["EMA20"]) if not np.isnan(latest["EMA20"]) else latest["Close"],
            "vwap": float(latest["VWAP"]) if not np.isnan(latest["VWAP"]) else latest["Close"],
            "rsi": float(latest["RSI"]) if not np.isnan(latest["RSI"]) else 50.0,
            "macd": float(latest["MACD"]) if not np.isnan(latest["MACD"]) else 0.0,
            "macd_signal": float(latest["MACD_Signal"]) if not np.isnan(latest["MACD_Signal"]) else 0.0,
            "macd_hist": float(latest["MACD_Hist"]) if not np.isnan(latest["MACD_Hist"]) else 0.0,
            "atr": float(latest["ATR"]) if not np.isnan(latest["ATR"]) else 50.0,
            "bb_upper": float(latest["BB_Upper"]) if not np.isnan(latest["BB_Upper"]) else latest["Close"] * 1.01,
            "bb_lower": float(latest["BB_Lower"]) if not np.isnan(latest["BB_Lower"]) else latest["Close"] * 0.99,
            "opening_range": or_data,
        }

        return res, scalars
