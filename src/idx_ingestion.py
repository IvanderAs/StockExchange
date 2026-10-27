import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import datetime
import os

# Create a folder to save our daily data
os.makedirs("IDX_Data", exist_ok=True)

def fetch_idx_market_data():
    print("Fetching IHSG and Top Bank Data...")
    # .JK is the Yahoo Finance suffix for IDX tickers
    tickers = ["^JKSE", "BBCA.JK", "BMRI.JK", "BBRI.JK", "GOTO.JK"]
    
    # Download today's data with 5-minute intervals
    data = yf.download(tickers, period="1d", interval="5m")
    return data

def scrape_kompas_finance():
    print("Scraping Kompas Money...")
    url = "https://money.kompas.com/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    headlines = []
    # Find the top 10 latest article titles
    for title in soup.find_all('h3', class_='article__title')[:10]:
        headlines.append(title.text.strip())
    
    return pd.DataFrame(headlines, columns=["Headline"])

if __name__ == "__main__":
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    print(f"--- AI Trading Pipeline: Ingestion Run {timestamp} ---")
    
    # 1. Gather Data
    market_data = fetch_idx_market_data()
    news_df = scrape_kompas_finance()
    
    # 2. Save Data to CSV for the AI to train on later
    market_data.to_csv(f"IDX_Data/market_{timestamp}.csv")
    news_df.to_csv(f"IDX_Data/news_kompas_{timestamp}.csv")
    
    print("Success! Data saved to IDX_Data folder.")

