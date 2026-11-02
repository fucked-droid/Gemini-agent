import pandas as pd
import unittest
from propose_multi_timeframe import aggregate_daily_to_weekly, add_weekly_regime_features, align_daily_weekly

class TestPointInTimeStability(unittest.TestCase):
    def test_point_in_time_stability(self):
        # Create daily series spanning 3 weeks
        dates = pd.date_range(start='2023-01-02', periods=15, freq='B')
        close_prices = [100, 101, 102, 103, 104,
                        105, 106, 107, 108, 109,
                        110, 111, 112, 113, 114]
        daily_df = pd.DataFrame({
            'Open': close_prices,
            'High': [p + 1 for p in close_prices],
            'Low': [p - 1 for p in close_prices],
            'Close': close_prices,
            'Volume': [1000] * 15,
            'Market_Regime': ['Bullish'] * 15
        }, index=dates)

        # Run alignment on full dataset
        weekly_full = aggregate_daily_to_weekly(daily_df)
        weekly_feat_full = add_weekly_regime_features(weekly_full)
        aligned_full = align_daily_weekly(daily_df, weekly_feat_full)

        # Run alignment on truncated dataset up to day 10 (end of week 2)
        truncated_df = daily_df.iloc[:10]
        weekly_trunc = aggregate_daily_to_weekly(truncated_df)
        weekly_feat_trunc = add_weekly_regime_features(weekly_trunc)
        aligned_trunc = align_daily_weekly(truncated_df, weekly_feat_trunc)

        # Verify that for all dates on or before the decision date (day 10),
        # the aligned features remain identical between full and truncated datasets.
        common_dates = aligned_trunc.index
        pd.testing.assert_frame_equal(
            aligned_full.loc[common_dates, ['EMA_9', 'EMA_21', 'Weekly_Trend', 'Multi_Timeframe_Aligned']],
            aligned_trunc[['EMA_9', 'EMA_21', 'Weekly_Trend', 'Multi_Timeframe_Aligned']]
        )
        print("Point-in-time stability test passed successfully! Features on or before decision date remain unchanged.")

if __name__ == '__main__':
    unittest.main()
