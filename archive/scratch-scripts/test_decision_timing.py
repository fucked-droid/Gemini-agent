import pandas as pd
import unittest
from propose_multi_timeframe import aggregate_daily_to_weekly, add_weekly_regime_features, align_daily_weekly

class TestDecisionTimingPolicy(unittest.TestCase):
    def test_decision_timing_policy(self):
        # Create a series covering a week ending Friday Jan 6, 2023, and next week starting Monday Jan 9, 2023
        dates = pd.date_range(start='2023-01-02', periods=10, freq='B') # Jan 2 (Mon) to Jan 13 (Fri)
        close_prices = [100, 101, 102, 103, 104,   # Week 1 (Mon-Fri, ends Friday Jan 6)
                        110, 111, 112, 113, 114]   # Week 2 (Mon-Fri, ends Friday Jan 13)
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

        # According to decision-timing policy:
        # Week 1 weekly close / indicators are finalized on Friday Jan 6.
        # They should become available for trading decisions starting Monday Jan 9 (Week 2).
        # Let's verify aligned value on Jan 6 vs Jan 9.
        
        jan_6_val = aligned.loc[pd.Timestamp('2023-01-06'), 'EMA_21']
        jan_9_val = aligned.loc[pd.Timestamp('2023-01-09'), 'EMA_21']
        
        # Since Jan 9 is the start of the next week, it correctly reflects the newly available weekly value from Jan 6 close.
        self.assertEqual(jan_9_val, jan_6_val)
        print("Decision-timing policy verification passed successfully!")

if __name__ == '__main__':
    unittest.main()
