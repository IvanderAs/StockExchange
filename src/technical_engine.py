import os
import glob
import pandas as pd
import pandas_ta as ta

os.makedirs("../data/technical", exist_ok=True)

def load_latest_market_file():
    """Finds and loads the latest market snapshot file, prioritizing full_market_*.csv."""
    files = glob.glob("../data/market/full_market_*.csv")
    if not files:
        files = glob.glob("../data/market/market_*.csv")
    if not files:
        print("❌ No market CSV found in ../data/market/")
        return None
    latest_file = max(files, key=os.path.getctime)
    print(f"📈 Processing market file: {latest_file}")
    return latest_file

def calculate_technical_indicators():
    market_file = load_latest_market_file()
    if not market_file:
        return

    # Read raw yfinance snapshot with multi-index header (Price type, Ticker)
    df_raw = pd.read_csv(market_file, header=[0, 1], index_col=0)
    
    technical_rows = []
    tickers = df_raw.columns.levels[1] if isinstance(df_raw.columns, pd.MultiIndex) else []

    for ticker in tickers:
        try:
            # Extract sub-dataframe for each ticker
            sub_df = df_raw.xs(ticker, axis=1, level=1).copy()
            sub_df.columns = [c.lower() for c in sub_df.columns]
            sub_df = sub_df.dropna(subset=['close', 'volume'])

            # Require minimum candles for indicator lookbacks
            if len(sub_df) < 14:
                continue

            # Calculate standard indicators via pandas-ta
            sub_df['RSI'] = ta.rsi(sub_df['close'], length=14)
            sub_df['SMA_20'] = ta.sma(sub_df['close'], length=20)
            
            # High/Low/Close for ATR
            if 'high' in sub_df.columns and 'low' in sub_df.columns:
                sub_df['ATR'] = ta.atr(sub_df['high'], sub_df['low'], sub_df['close'], length=14)
            else:
                sub_df['ATR'] = sub_df['close'] * 0.02 # Fallback volatility estimate

            sub_df['Ticker'] = ticker
            
            # Keep valid rows where key indicators are populated
            valid_rows = sub_df.dropna(subset=['RSI', 'close'])
            if not valid_rows.empty:
                technical_rows.append(valid_rows)

        except Exception as e:
            continue

    if not technical_rows:
        print("⚠️ No valid technical indicators generated.")
        return

    # Combine into single feature set
    df_technical = pd.concat(technical_rows).reset_index()
    
    now_str = pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M")
    out_file = f"../data/technical/technical_{now_str}.csv"
    df_technical.to_csv(out_file, index=False)
    print(f"✅ Technical indicators calculated and saved to: {out_file}")

if __name__ == "__main__":
    calculate_technical_indicators()
