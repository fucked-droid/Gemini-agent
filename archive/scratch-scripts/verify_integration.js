const { execFile } = require("child_process");
const PYTHON = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe";
const ENGINE_DIR = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine";

const importScript = `
import sys
sys.path.insert(0, '.')
from src.multi_timeframe import aggregate_daily_to_weekly, add_weekly_regime_features, align_daily_weekly
import pandas as pd

df = pd.DataFrame({
    'Open': [100, 101, 102, 103, 104, 105],
    'High': [102, 103, 104, 105, 106, 107],
    'Low': [99, 100, 101, 102, 103, 104],
    'Close': [101, 102, 103, 104, 105, 106],
    'Volume': [1000]*6
}, index=pd.date_range('2023-01-01', periods=6, freq='B'))

weekly = aggregate_daily_to_weekly(df)
feat = add_weekly_regime_features(weekly)
aligned = align_daily_weekly(df, feat)
print("Integration smoke test passed successfully! Shape:", aligned.shape)
`;

execFile(PYTHON, ["-c", importScript], { cwd: ENGINE_DIR }, (err, stdout, stderr) => {
  console.log("ERR:", err);
  console.log("STDOUT:", stdout);
  console.log("STDERR:", stderr);
});
