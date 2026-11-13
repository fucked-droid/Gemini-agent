const { execFile } = require("child_process");
const PYTHON = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine\\.venv\\Scripts\\python.exe";
const ENGINE_DIR = "H:\\My Drive\\Sahil Sangare\\Practice\\Daily-Market-Regime-Engine";

const validationScript = `
import pandas as pd
from pathlib import Path

def validate_dataframe(df):
    # Check datetime index or date column
    has_datetime_index = isinstance(df.index, pd.DatetimeIndex)
    has_date_col = 'Date' in df.columns or 'date' in df.columns
    
    if not has_datetime_index and not has_date_col:
        raise ValueError("No usable date column or DatetimeIndex found.")
        
    # Check OHLC columns
    required_ohlc = ['Open', 'High', 'Low', 'Close']
    missing_ohlc = [col for col in required_ohlc if col not in df.columns]
    if missing_ohlc:
        raise ValueError(f"Missing OHLC columns: {missing_ohlc}")
        
    print("Validation passed successfully!")
    print(f"DatetimeIndex present: {has_datetime_index}")
    print(f"OHLC columns present: {required_ohlc}")

parquet_path = Path("data/nifty_df_master.parquet")
df = pd.read_parquet(parquet_path)
validate_dataframe(df)
`;

execFile(PYTHON, ["-c", validationScript], { cwd: ENGINE_DIR }, (err, stdout, stderr) => {
  console.log("ERR:", err);
  console.log("OUT:\n", stdout);
  console.log("STDERR:\n", stderr);
});
