import sqlite3
import requests
import time
import os

DB_PATH = "../data/idx_trading.db"
API_TOKEN = "YOUR_GOAPI_TOKEN" # Replace with actual API Token

def fetch_live_prices_realtime(tickers):
    """Fetches real-time price ticks for list of tickers from GoAPI or streaming endpoint."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ensure signals table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS realtime_quotes (
            ticker TEXT PRIMARY KEY,
            price REAL,
            change_pct REAL,
            volume INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    formatted_tickers = [t.replace(".JK", "") for t in tickers]
    
    # Example endpoint fetching real-time market depth / last price
    url = f"https://api.goapi.io/v1/stock/idx/prices?api_key={API_TOKEN}"
    
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json().get('data', {}).get('results', [])
            for item in data:
                ticker_symbol = f"{item['symbol']}.JK"
                if ticker_symbol in tickers or item['symbol'] in formatted_tickers:
                    price = float(item['close'])
                    change_pct = float(item.get('change_percentage', 0.0))
                    vol = int(item.get('volume', 0))

                    cursor.execute("""
                        INSERT INTO realtime_quotes (ticker, price, change_pct, volume, updated_at)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(ticker) DO UPDATE SET
                            price=excluded.price,
                            change_pct=excluded.change_pct,
                            volume=excluded.volume,
                            updated_at=CURRENT_TIMESTAMP;
                    """, (ticker_symbol, price, change_pct, vol))
            conn.commit()
            print(f"⚡ Real-Time Ticks Updated at {time.strftime('%H:%M:%S')}")
    except Exception as e:
        print(f"⚠️ Realtime tick update error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # Test streaming loop for active portfolio & watchlist
    active_tickers = ["BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "BBNI.JK"]
    fetch_live_prices_realtime(active_tickers)
