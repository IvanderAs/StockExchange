import feedparser
import yfinance as yf
import pandas as pd
import datetime
import os

# Create folder structure for daily data
os.makedirs("data/market", exist_ok=True)
os.makedirs("data/news", exist_ok=True)

# 1. RSS Feed Sources (Indonesian & Global Macro)
RSS_FEEDS = {
    "CNBC_Indo": "https://www.cnbcindonesia.com/market/rss",
    "Kompas_Money": "https://money.kompas.com/rss",
    "Antara_Ekon": "https://www.antaranews.com/rss/ekonomi",
    "BBC_World": "http://feeds.bbci.co.uk/news/business/rss.xml"
}

# 2. Key Tickers to Monitor (Indices, Top Banks, Commodities)
TICKERS = [
    "^JKSE",     # IHSG Index
    "BBCA.JK",   # Bank BCA
    "BMRI.JK",   # Bank Mandiri
    "BBRI.JK",   # Bank BRI
    "GOTO.JK",   # GoTo
    "CL=F",      # Crude Oil Futures
    "GC=F"       # Gold Futures
]

def fetch_rss_news():
    headlines = []
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]: # Top 10 articles per source
                headlines.append({
                    "timestamp": timestamp,
                    "source": source,
                    "title": entry.title,
                    "link": entry.link,
                    "published": getattr(entry, 'published', timestamp)
                })
        except Exception as e:
            print(f"Error fetching {source}: {e}")
            
    return pd.DataFrame(headlines)

def fetch_market_prices():
    # Fetch 1-day interval data with 5-minute granularity
    data = yf.download(TICKERS, period="1d", interval="5m", progress=False)
    return data

if __name__ == "__main__":
    now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    print(f" Running Multi-Source Data Collection [{now_str}]...")

    # Fetch and Save News
    df_news = fetch_rss_news()
    news_file = f"data/news/news_{now_str}.csv"
    df_news.to_csv(news_file, index=False)
    print(f" Saved {len(df_news)} news headlines to {news_file}")

    # Fetch and Save Market Data
    df_market = fetch_market_prices()
    market_file = f"data/market/market_{now_str}.csv"
    df_market.to_csv(market_file)
    print(f" Saved market snapshot to {market_file}")

    print(" Complete!")
