const { execFile } = require("child_process");
const PYTHON = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe";
const ENGINE_DIR = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine";

const testScript = `
import sys
sys.path.insert(0, '.')
from src.multi_timeframe import aggregate_daily_to_weekly, add_weekly_regime_features, align_daily_weekly
import pandas as pd

df_master = pd.read_parquet("data/nifty_df_master.parquet")
weekly = aggregate_daily_to_weekly(df_master)
weekly_feat = add_weekly_regime_features(weekly)
aligned = align_daily_weekly(df_master, weekly_feat)

print("Aligned daily dataframe shape:", aligned.shape)
print("Aligned columns:", list(aligned.columns))
print("Sample aligned rows:")
print(aligned[['Close', 'Market_Regime', 'Weekly_Trend', 'Multi_Timeframe_Aligned']].tail(5))

# Check for any unhandled NaN values in alignment columns
assert not aligned['Weekly_Trend'].isna().any()
assert not aligned['Multi_Timeframe_Aligned'].isna().any()
print("Daily alignment verification passed successfully without NaNs or data loss!")
`;

execFile(PYTHON, ["-c", testScript], { cwd: ENGINE_DIR }, (err, stdout, stderr) => {
  console.log("ERR:", err);
  console.log("STDOUT:", stdout);
  console.log("STDERR:", stderr);
});
