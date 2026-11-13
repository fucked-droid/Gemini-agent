const { execFile } = require("child_process");
const PYTHON = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe";
const ENGINE_DIR = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine";

const checkScript = `
import pandas as pd
from pathlib import Path

parquet_path = Path("data/nifty_df_master.parquet")
df = pd.read_parquet(parquet_path)

# Check for missing sessions / business day gaps
full_idx = pd.date_range(start=df.index.min(), end=df.index.max(), freq='B')
missing = full_idx.difference(df.index)

print(f"Total rows: {len(df)}")
print(f"Business days expected between {df.index.min().date()} and {df.index.max().date()}: {len(full_idx)}")
print(f"Missing sessions count: {len(missing)}")
if len(missing) > 0:
    print("Sample missing dates:", missing[:10].strftime('%Y-%m-%d').tolist())
else:
    print("No missing business sessions!")
`;

execFile(PYTHON, ["-c", checkScript], { cwd: ENGINE_DIR }, (err, stdout, stderr) => {
  console.log("ERR:", err);
  console.log("OUT:\n", stdout);
  console.log("STDERR:\n", stderr);
});
