import os
import glob
import sqlite3
import pandas as pd
import numpy as np

DB_PATH = "../data/idx_trading.db"

def generate_signals():
    print("🚀 Starting XAI Signal Generation...")
    tech_files = glob.glob("../data/technical/technical_*.csv")
    if not tech_files:
        print("⚠️ No technical files found in ../data/technical/")
        return

    latest_file = max(tech_files, key=os.path.getctime)
    print(f"📄 Processing latest dataset: {latest_file}")
    
    try:
        df = pd.read_csv(latest_file)
    except Exception as e:
        print(f"❌ Failed to read CSV: {e}")
        return

    if df.empty:
        print("⚠️ Technical DataFrame is empty.")
        return

    os.makedirs("../data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ensure table structure exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS xai_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL,
        price REAL NOT NULL,
        signal TEXT NOT NULL,
        confidence REAL NOT NULL,
        stop_loss REAL,
        take_profit REAL,
        category TEXT,
        explanations TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    for idx, row in df.iterrows():
        try:
            ticker = str(row.get('Ticker', row.get('ticker', 'UNKNOWN')))
            if ticker == 'UNKNOWN' or not ticker:
                continue

            # Safely parse numeric features
            price = float(row.get('close', row.get('Price', row.get('price', 0.0))))
            rsi = float(row.get('RSI', row.get('rsi', 50.0)))
            sma = float(row.get('SMA_20', row.get('sma_20', price)))
            atr = float(row.get('ATR', row.get('atr', price * 0.02)))
            vol = float(row.get('volume', row.get('Volume', 0.0)))
            sentiment = float(row.get('Sentiment_Score', row.get('sentiment_score', 0.0)))

            if np.isnan(price) or price <= 0:
                continue

            if np.isnan(rsi): rsi = 50.0
            if np.isnan(sma): sma = price
            if np.isnan(atr): atr = price * 0.02
            if np.isnan(sentiment): sentiment = 0.0

            # Rule-based Signal Calculation
            conf = 50.0
            signal = "HOLD"
            explanations = []

            if rsi < 35:
                conf += 20.0
                signal = "BUY"
                explanations.append(f"Oversold RSI ({rsi:.1f}) indicates potential reversal")
            elif rsi > 65:
                conf += 15.0
                signal = "SELL"
                explanations.append(f"Overbought RSI ({rsi:.1f}) suggests downside risk")

            if price > sma:
                if signal == "BUY": conf += 15.0
                explanations.append(f"Trading above 20-period SMA (Rp {sma:,.2f})")
            else:
                if signal == "SELL": conf += 15.0
                explanations.append(f"Trading below 20-period SMA (Rp {sma:,.2f})")

            if sentiment > 0.15:
                conf += 10.0
                explanations.append(f"Positive news sentiment (+{sentiment:.2f})")
            elif sentiment < -0.15:
                conf -= 10.0
                explanations.append(f"Negative news sentiment ({sentiment:.2f})")

            conf = min(max(conf, 15.0), 95.0)

            # Categorization
            category = "Safe & Recommended 🟢" if conf >= 75.0 else "Need Observation 🟡"
            if vol < 10000 and price < 200:
                category = "Gorengan / High Risk 🔴"
                if conf < 65:
                    signal = "BLOCKED (High Risk)"

            exp_str = " | ".join(explanations) if explanations else "Standard technical observation"

            cursor.execute("""
                INSERT INTO xai_signals (ticker, price, signal, confidence, stop_loss, take_profit, category, explanations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (ticker, price, signal, conf, price - (1.5 * atr), price + (2.0 * atr), category, exp_str))

        except Exception as row_err:
            print(f"⚠️ Error processing row {idx}: {row_err}")
            continue

    conn.commit()
    conn.close()
    print("✅ XAI Signal Generation finished successfully!")

if __name__ == "__main__":
    generate_signals()
