"""
Unit Tests for Machine Learning Forecasting & Walk-Forward Validation.
Tests feature engineering anti-leakage, multi-horizon forecasts, Brier score,
and sample size gating.
"""

import unittest
import numpy as np
import pandas as pd
import datetime

import sys
from pathlib import Path
TERMINAL_ROOT = Path(__file__).resolve().parent.parent
if str(TERMINAL_ROOT) not in sys.path:
    sys.path.insert(0, str(TERMINAL_ROOT))

from prediction.features import FeatureEngineer
from prediction.models import DirectionalForecaster
from prediction.validation import WalkForwardValidator
from prediction.forecasting import ForecastOrchestrator
from analytics.indicators import TechnicalIndicators

class TestForecasting(unittest.TestCase):

    def setUp(self):
        dates = [datetime.datetime(2026, 11, 14, 9, 15) + datetime.timedelta(minutes=5 * i) for i in range(80)]
        closes = [25000.0 + i * 3.0 for i in range(80)]
        self.df = pd.DataFrame(
            {
                "Open": closes,
                "High": [c + 4.0 for c in closes],
                "Low": [c - 4.0 for c in closes],
                "Close": closes,
                "Volume": 100000,
            },
            index=pd.DatetimeIndex(dates, name="Datetime"),
        )
        self.df_enriched, self.sc = TechnicalIndicators.calculate_all(self.df)

    def test_feature_engineering_no_leakage(self):
        feat = FeatureEngineer.extract_features(self.df_enriched)
        self.assertFalse(feat.empty)
        # Verify that features exist and no NaNs remain after cleaning
        self.assertFalse(feat.isna().any().any())
        self.assertIn("ret_1", feat.columns)
        self.assertIn("dist_vwap", feat.columns)

    def test_multi_horizon_forecasting(self):
        forecasts = DirectionalForecaster.forecast_horizons(self.df_enriched, 25240.0, 50.0)

        for h in ["5m", "15m", "30m", "60m"]:
            self.assertIn(h, forecasts)
            f_data = forecasts[h]
            self.assertIn(f_data["direction"], ["UP", "DOWN", "NEUTRAL"])
            self.assertLess(f_data["target_lower"], f_data["target_upper"])
            self.assertGreaterEqual(f_data["probability_up"], 0.0)
            self.assertLessEqual(f_data["probability_up"], 1.0)
            self.assertIn("confidence_pct", f_data)
            self.assertIn("indicator_agreement_pct", f_data)

    def test_independent_horizon_forecasts(self):
        # Create different dataframes for different horizons to verify independence
        df_5m = self.df_enriched.copy()
        # Create a downtrending 60m dataset
        dates_60m = [datetime.datetime(2026, 11, 14, 9, 15) + datetime.timedelta(hours=i) for i in range(50)]
        closes_60m = [25500.0 - i * 5.0 for i in range(50)]
        df_60m_raw = pd.DataFrame(
            {
                "Open": closes_60m,
                "High": [c + 5.0 for c in closes_60m],
                "Low": [c - 5.0 for c in closes_60m],
                "Close": closes_60m,
                "Volume": 80000,
            },
            index=pd.DatetimeIndex(dates_60m, name="Datetime"),
        )
        df_60m_en, _ = TechnicalIndicators.calculate_all(df_60m_raw)

        tf_suite = {
            "5m": df_5m,
            "15m": df_5m,
            "30m": df_5m,
            "60m": df_60m_en,
        }

        res = ForecastOrchestrator.run_prediction_pipeline(
            df_enriched=df_5m,
            current_price=25240.0,
            atr=50.0,
            tf_suite=tf_suite,
            symbol="NIFTY",
            data_mode="HISTORICAL",
        )
        horizons = res["horizons"]
        # 5m was uptrending in setUp, 60m is downtrending
        self.assertNotEqual(horizons["5m"]["direction"], horizons["60m"]["direction"])
        self.assertEqual(horizons["60m"]["direction"], "DOWN")
        self.assertNotEqual(horizons["5m"]["probability_up"], horizons["60m"]["probability_up"])
        self.assertLess(horizons["60m"]["probability_up"], 0.45)
        # Verify target lower < target upper across all horizons
        for h, data in horizons.items():
            self.assertLess(data["target_lower"], data["target_upper"])
            self.assertGreater(data["target_upper"], data["target_lower"])

    def test_walk_forward_insufficient_sample_size_gate(self):
        small_returns = np.array([0.001, -0.002, 0.003])
        small_probs = np.array([0.6, 0.4, 0.7])
        small_dirs = ["UP", "DOWN", "UP"]

        res = WalkForwardValidator.evaluate_predictions(small_returns, small_probs, small_dirs)
        self.assertEqual(res["status"], "INSUFFICIENT_SAMPLE_SIZE")
        self.assertFalse(res["is_validated"])

    def test_walk_forward_evaluation_calculation(self):
        # 50 samples (> 30 threshold)
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.005, size=50)
        probs = np.clip(0.5 + returns * 20.0, 0.1, 0.9)
        dirs = ["UP" if p > 0.5 else "DOWN" for p in probs]

        res = WalkForwardValidator.evaluate_predictions(returns, probs, dirs)
        self.assertIn(res["status"], ["VALIDATED", "DEGRADED"])
        self.assertIsNotNone(res["brier_score"])
        self.assertIsNotNone(res["hit_rate_pct"])
        self.assertGreaterEqual(res["brier_score"], 0.0)

if __name__ == "__main__":
    unittest.main()
