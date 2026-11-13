import pandas as pd
import unittest
from propose_multi_timeframe import aggregate_daily_to_weekly, add_weekly_regime_features, align_daily_weekly

class TestWeeklyFeatureAlignment(unittest.TestCase):
    def test_weekly_feature_alignment_exact(self):
        # Create daily business days across 2 weeks (e.g. Jan 2023)
        dates = pd.date_range(start='2023-01-02', periods=10, freq='B') # Mon-Fri, Mon-Fri
        # Week 1 ends Jan 6 (Fri), Week 2 ends Jan 13 (Fri)
        close_prices = [100, 102, 104, 106, 108,   # Week 1
                        110, 112, 114, 116, 118]   # Week 2
        daily_df = pd.DataFrame({
            'Open': close_prices,
            'High': [p + 1 for p in close_prices],
            'Low': [p - 1 for p in close_prices],
            'Close': close_prices,
            'Volume': [1000] * 10,
            'Market_Regime': ['Bullish'] * 10
        }, index=dates)

        weekly = aggregate_daily_to_weekly(daily_df)
        weekly_feat = add_weekly_regime_features(weekly)
        aligned = align_daily_weekly(daily_df, weekly_feat)

        # Verify alignment columns exist
        self.assertIn('EMA_9', aligned.columns)
        self.assertIn('EMA_21', aligned.columns)
        self.assertIn('Weekly_Trend', aligned.columns)
        self.assertEqual(len(aligned), len(daily_df))

        # Verify no NaN values in aligned feature columns for dates >= first weekly close
        self.assertFalse(aligned['Weekly_Trend'].isna().any())
        print("Weekly feature alignment exact test passed successfully!")

if __name__ == '__main__':
    unittest.main()
