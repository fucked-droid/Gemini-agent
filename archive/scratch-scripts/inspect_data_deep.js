const { execFile } = require("child_process");
const PYTHON = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe";
const ENGINE_DIR = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine";

const script = `
import sys
import pandas as pd
from pathlib import Path

data_dir = Path("data")
parquet_path = data_dir / "nifty_df_master.parquet"
csv_path = data_dir / "nifty_df_master.csv"

print("--- PARQUET INSPECTION ---")
df_pq = pd.read_parquet(parquet_path)
print("Shape:", df_pq.shape)
print("Columns:", list(df_pq.columns))
print("Index type:", type(df_pq.index))
print("Start date:", df_pq.index.min())
print("End date:", df_pq.index.max())
print("Frequency inferred:", pd.infer_freq(df_pq.index))
print("Head:\\n", df_pq.head(2))

print("\\n--- CSV INSPECTION ---")
df_csv = pd.read_csv(csv_path, nrows=5)
print("CSV Columns:", list(df_csv.columns))
print(df_csv)
`;

execFile(PYTHON, ["-c", script], { cwd: ENGINE_DIR }, (err, stdout, stderr) => {
  console.log("ERR:", err);
  console.log("OUT:\n", stdout);
  console.log("STDERR:\n", stderr);
});
