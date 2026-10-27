import os
import glob
import pandas as pd
import numpy as np
from xgboost import XGBClassifier

def load_latest_file(pattern):
    files = glob.glob(pattern)
    return max(files, key=os.path.getctime) if files else None

def generate_signals():
    # 1. Load latest technical dataset
    tech_file = load_latest_file("../data/technical/technical_*.csv")
    if not tech_file:
        print("❌ Technical dataset not found in data/technical/")
        return

    df = pd.read_csv(tech_file)
    
    # 2. Load safe categorized tickers
    safe_file = load_latest_file("../data/categorized/safe/safe_*.csv")
    safe_tickers = []
    if safe_file:
        safe_df = pd.read_csv(safe_file)
        if 'ticker' in safe_df.columns:
            safe_tickers = safe_df['ticker'].tolist()

    # 3. Load trained model artifact
    model_path = "../models/xgb_idx_sentiment_aware.json"
    if not os.path.exists(model_path):
        model_path = "../models/xgb_idx_model.json"
        
    if not os.path.exists(model_path):
        print("❌ Trained model file not found. Run train_multi_horizon.py first!")
        return

    model = XGBClassifier()
    model.load_model(model_path)

    # 4. Feature vector setup
    feature_cols = ['RSI', 'ATR', 'SMA_20', 'close', 'volume']
    if 'Sentiment_Score' not in df.columns:
        df['Sentiment_Score'] = 0.0
    feature_cols.append('Sentiment_Score')

    # Get latest snapshot per ticker
    valid_df = df.dropna(subset=feature_cols).copy()
    if 'Ticker' in valid_df.columns:
        valid_df = valid_df.groupby('Ticker').last().reset_index()

    if valid_df.empty:
        print("⚠️ No valid rows found for signal generation.")
        return

    # Run inference
    X_live = valid_df[feature_cols]
    valid_df['Up_Probability'] = model.predict_proba(X_live)[:, 1]

    # Containers for results
    buy_signals = []
    sell_signals = []

    for idx, row in valid_df.iterrows():
        ticker = row.get('Ticker', 'UNKNOWN')
        price = row['close']
        atr = row['ATR']
        prob = row['Up_Probability']

        # Skip indices/macro futures
        if ticker in ["^JKSE", "CL=F", "GC=F"]:
            continue

        # Ignore illiquid/gorengan stocks for BUY consideration
        is_safe = (not safe_tickers) or (ticker in safe_tickers)

        if prob >= 0.60 and is_safe:
            sl = price - (1.5 * atr)
            tp = price + (3.0 * atr)
            buy_signals.append({
                'ticker': ticker,
                'price': price,
                'confidence': prob * 100,
                'sl': sl,
                'tp': tp
            })
        elif prob <= 0.40:
            sell_signals.append({
                'ticker': ticker,
                'price': price,
                'confidence': (1.0 - prob) * 100
            })

    # Sort candidates by AI confidence
    buy_signals = sorted(buy_signals, key=lambda x: x['confidence'], reverse=True)
    sell_signals = sorted(sell_signals, key=lambda x: x['confidence'], reverse=True)

    print("\n=======================================================")
    print("       🟢 1. AI CONFIDENT BUY CANDIDATES (PASSED SAFE)")
    print("=======================================================")
    if not buy_signals:
        print("No high-confidence BUY signals found for safe tickers in this snapshot.")
    else:
        for item in buy_signals:
            print(f"Ticker        : {item['ticker']}")
            print(f"  Price       : Rp {item['price']:,.2f}")
            print(f"  Confidence  : {item['confidence']:.1f}%")
            print(f"  Cut-Loss    : Rp {item['sl']:,.2f}")
            print(f"  Take-Profit : Rp {item['tp']:,.2f}\n")

    print("=======================================================")
    print("       🔴 2. AI CONFIDENT SELL CANDIDATES")
    print("=======================================================")
    if not sell_signals:
        print("No high-confidence SELL signals found in this snapshot.")
    else:
        for item in sell_signals:
            print(f"Ticker        : {item['ticker']}")
            print(f"  Price       : Rp {item['price']:,.2f}")
            print(f"  Confidence  : {item['confidence']:.1f}% (Bearish)\n")
    print("=======================================================\n")

if __name__ == "__main__":
    generate_signals()
