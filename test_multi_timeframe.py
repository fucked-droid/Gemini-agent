import pandas as pd
import unittest
from propose_multi_timeframe import aggregate_daily_to_weekly, add_weekly_regime_features, align_daily_weekly

class TestMultiTimeframe(unittest.TestCase):
    def test_aggregation_and_alignment(s):
        # Create dummy daily data
        dates = pd.date_range(start='2023-01-01', periods=20, freq='B')
        data = {
            'Open': range(100, 120),
            'High': range(105, 125),
            'Low': range(95, 115),
            'Close': range(102, 122),
            'Volume': [1000] * 20,
            'Market_Regime': ['Bullish'] * 20
        }
        daily_df = pd.DataFrame(data, index=dates)
        
        weekly = aggregate_daily_to_weekly(daily_df)
        s.assertFalse(weekly.empty)
        s.assertIn('Close', weekly.columns)
        
        weekly_feat = add_weekly_regime_features(weekly)
        s.assertIn('Weekly_Trend', weekly_feat.columns)
        
        aligned = align_daily_weekly(daily_df, weekly_feat)
        s.assertIn('Weekly_Trend', aligned.columns)
        s.assertIn('Multi_Timeframe_Aligned', aligned.columns)
        s.assertEqual(len(aligned), len(daily_df))

if __name__ == '__main__':
    unittest.main()
