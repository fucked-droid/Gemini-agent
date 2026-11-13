import pandas as pd
import unittest
from propose_multi_timeframe import aggregate_daily_to_weekly, add_weekly_regime_features, align_daily_weekly

class TestMultiTimeframeRobustness(unittest.TestCase):
    def test_unsorted_and_duplicate_dates(self):
        dates = pd.to_datetime(['2023-01-05', '2023-01-02', '2023-01-03', '2023-01-03']) # Unsorted & duplicate
        data = {
            'Open': [100, 95, 98, 99],
            'High': [105, 98, 102, 103],
            'Low': [95, 90, 94, 95],
            'Close': [102, 92, 100, 101],
            'Volume': [100, 100, 100, 100]
        }
        df = pd.DataFrame(data, index=dates)
        weekly = aggregate_daily_to_weekly(df)
        self.assertFalse(weekly.empty)
        # Should be sorted and deduplicated
        self.assertTrue(weekly.index.is_monotonic_increasing)

    def test_missing_ohlc_columns(self):
        df = pd.DataFrame({'Close': [100]}, index=pd.date_range('2023-01-01', periods=1))
        with self.assertRaises(ValueError):
            aggregate_daily_to_weekly(df)

    def test_input_mutation_prevention(self):
        dates = pd.date_range('2023-01-01', periods=5, freq='B')
        df = pd.DataFrame({
            'Open': [100]*5, 'High': [105]*5, 'Low': [95]*5, 'Close': [100]*5
        }, index=dates)
        orig_cols = list(df.columns)
        weekly = aggregate_daily_to_weekly(df)
        self.assertEqual(list(df.columns), orig_cols)

if __name__ == '__main__':
    unittest.main()
