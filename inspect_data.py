import pandas as pd
p = r"H:\My Drive\Sahil Sangare\Practice\Daily-Market-Regime-Engine"
master_csv = r"H:\My Drive\Sahil Sangare\Practice\Daily-Market-Regime-Engine\data\nifty_df_master.csv"
df = pd.read_csv(master_csv)
print("Columns:", df.columns.tolist())
print("Shape:", df.shape)
if 'date' in df.columns:
    df['date'] = pd.to_datetime(df['date'])
    print("Date range:", df['date'].min(), "to", df['date'].max())
elif 'Date' in df.columns:
    df['Date'] = pd.to_datetime(df['Date'])
    print("Date range:", df['Date'].min(), "to", df['Date'].max())
print(df.head(2))
