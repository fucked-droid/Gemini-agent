const { execFile } = require("child_process");
const PYTHON = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe";
const ENGINE_DIR = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine";

const testScript = `
import sys
sys.path.insert(0, '.')
from src.multi_timeframe import aggregate_daily_to_weekly, add_weekly_regime_features, align_daily_weekly
import pandas as pd
import numpy as np

# Load real master data if available, or generate synthetic weekly trend test
df_master = pd.read_parquet("data/nifty_df_master.parquet")
weekly = aggregate_daily_to_weekly(df_master)
weekly_feat = add_weekly_regime_features(weekly)

print("Weekly features head:")
print(weekly_feat[['Close', 'EMA_9', 'EMA_21', 'Weekly_Trend']].head(10))

# Verify weekly trend feature properties
assert 'Weekly_Trend' in weekly_feat.columns
assert set(weekly_feat['Weekly_Trend'].unique()).issubset({'Bullish', 'Bearish'})
print("Weekly trend features verified successfully on master dataset!")
`;

execFile(PYTHON, ["-c", testScript], { cwd: ENGINE_DIR }, (err, stdout, stderr) => {
  console.log("ERR:", err);
  console.log("STDOUT:", stdout);
  console.log("STDERR:", stderr);
});
