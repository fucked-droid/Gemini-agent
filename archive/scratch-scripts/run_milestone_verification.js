const { execFile } = require("child_process");
const PYTHON = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe";
const ENGINE_DIR = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine";

console.log("Running final verification suite for Daily-Market-Regime-Engine multi-timeframe milestone...");

execFile(PYTHON, ["-c", "import sys; sys.path.insert(0, '.'); from src.multi_timeframe import aggregate_daily_to_weekly, add_weekly_regime_features, align_daily_weekly; import pandas as pd; df = pd.read_parquet('data/nifty_df_master.parquet'); weekly = aggregate_daily_to_weekly(df); feat = add_weekly_regime_features(weekly); aligned = align_daily_weekly(df, feat); print('MILESTONE VERIFICATION SUCCESS: Rows:', len(aligned), 'Columns:', len(aligned.columns))"], { cwd: ENGINE_DIR }, (err, stdout, stderr) => {
  console.log("ERR:", err);
  console.log("STDOUT:", stdout);
  console.log("STDERR:", stderr);
});
