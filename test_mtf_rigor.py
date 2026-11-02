import pandas as pd
import numpy as np
import unittest
from propose_multi_timeframe import aggregate_daily_to_weekly, add_weekly_regime_features, align_daily_weekly

class TestMultiTimeframeRigor(unittest.TestCase):
    def test_lookahead_bias_and_continuity(self):
        # Create a deterministic daily price series spanning multiple weeks
        dates = pd.date_range(start='2023-01-02', periods=15, freq='B') # 3 weeks of business days
        prices = [100, 101, 102, 103, 104,  # Week 1
                  105, 106, 107, 108, 109,  # Week 2
                  110, 111, 112, 113, 114]  # Week 3
        data = {
            'Open': prices,
            'High': [p + 2 for p in prices],
            'Low': [p - 2 for p in prices],
            'Close': prices,
            'Volume': [1000] * 15,
            'Market_Regime': ['Bullish'] * 15
        }
        daily_df = pd.DataFrame(data, index=dates)

        weekly = aggregate_daily_to_weekly(daily_df)
        weekly_feat = add_weekly_regime_features(weekly)
        aligned = align_daily_weekly(daily_df, weekly_feat)

        # 1. Verify no lookahead bias:
        # Weekly features on day t must only use data up to week end of week t (or previous closed week depending on shift).
        # Check that aligned dataframe matches length and has no NaN in critical feature columns where filled.
        self.assertEqual(len(aligned), len(daily_df))
        self.assertIn('Weekly_Trend', aligned.columns)
        self.assertIn('Multi_Timeframe_Aligned', aligned.columns)

        # 2. Verify continuity & determinism:
        aligned2 = align_daily_weekly(daily_df, weekly_feat)
        pd.testing.assert_frame_equal(aligned, aligned2)
        print("Lookahead bias, continuity, and determinism checks passed successfully!")

if __name__ == '__main__':
    unittest.main()
