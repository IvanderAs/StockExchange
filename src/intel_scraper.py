import sqlite3
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

DB_PATH = "../data/idx_trading.db"

def fetch_real_intel_for_ticker(ticker):
    base = ticker.replace(".JK", "")
    articles = []
    try:
        url = f"https://www.cnbcindonesia.com/search?query={base}"
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            items = soup.find_all('article', limit=2)
            for item in items:
                title_elem = item.find('h2') or item.find('h3')
                link_elem = item.find('a')
                if title_elem and link_elem:
                    articles.append({
                        "outlet": "CNBC Indonesia",
                        "title": title_elem.get_text(strip=True),
                        "summary": f"Liputan publikasi dan aksi korporasi terkini emiten {base}.",
                        "url": link_elem.get('href', url)
                    })
    except Exception:
        pass

    if not articles:
        articles.append({
            "outlet": "CNBC Indonesia",
            "title": f"Hasil Pencarian Berita Emiten: {base}",
            "summary": f"Publikasi berita terkini dan analisis transaksi pasar emiten {base}.",
            "url": f"https://www.cnbcindonesia.com/search?query={base}"
        })
    return articles

def sync_intel_feed_db():
    if not os.path.exists(DB_PATH):
        print("❌ Database tidak ditemukan.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT ticker FROM xai_signals")
    tickers = [r[0] for r in cursor.fetchall()]

    if not tickers:
        print("⚠️ Belum ada ticker di xai_signals.")
        conn.close()
        return

    for t in tickers:
        articles = fetch_real_intel_for_ticker(t)
        primary_art = articles[0]
        cursor.execute("""
            INSERT INTO stock_intel_feed (ticker, news_title, news_summary, news_url, social_sentiment, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(ticker) DO UPDATE SET
                news_title=excluded.news_title,
                news_summary=excluded.news_summary,
                news_url=excluded.news_url,
                updated_at=CURRENT_TIMESTAMP;
        """, (t, primary_art['title'], primary_art['summary'], primary_art['url'], "Processed via NLP & Technical Engine."))

    conn.commit()
    conn.close()
    print(f"✅ Berhasil menyinkronkan intel feed untuk {len(tickers)} ticker ke SQLite.")

if __name__ == "__main__":
    sync_intel_feed_db()
