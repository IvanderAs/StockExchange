import sqlite3
import os

DB_PATH = "../data/idx_trading.db"

def get_connection():
    os.makedirs("../data", exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Market Categories
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS market_categories (
        ticker TEXT PRIMARY KEY,
        category TEXT NOT NULL,
        last_price REAL,
        daily_turnover REAL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. XAI Signals Table
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

    # 3. Watchlist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS watchlist (
        ticker TEXT PRIMARY KEY,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. Portfolio
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portfolio (
        ticker TEXT PRIMARY KEY,
        shares_owned INTEGER NOT NULL,
        avg_buy_price REAL NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 5. Drop old table and create updated Stock Intel Feed
    cursor.execute("DROP TABLE IF EXISTS stock_intel_feed;")
    cursor.execute("""
    CREATE TABLE stock_intel_feed (
        ticker TEXT PRIMARY KEY,
        news_title TEXT,
        news_summary TEXT,
        news_url TEXT,
        social_sentiment TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()
    print("✅ Database & Tabel stock_intel_feed berhasil diperbarui.")

if __name__ == "__main__":
    init_db()
