import os
import glob
import pandas as pd
import pandas_ta as ta

os.makedirs("../data/categorized/safe", exist_ok=True)
os.makedirs("../data/categorized/observation", exist_ok=True)
os.makedirs("../data/categorized/gorengan", exist_ok=True)

def get_latest_market_file():
    files = glob.glob("../data/market/full_market_*.csv")
    if not files:
        files = glob.glob("../data/market/market_*.csv")
    return max(files, key=os.path.getctime) if files else None

def categorize_stocks():
    latest_file = get_latest_market_file()
    if not latest_file:
        print("❌ Tidak ada data pasar ditemukan.")
        return

    print(f"📊 Menjalankan Dynamic Classifier pada: {latest_file}")
    df = pd.read_csv(latest_file, header=[0, 1], index_col=0)

    safe_list = []
    obs_list = []
    gorengan_list = []

    tickers = df.columns.levels[1] if isinstance(df.columns, pd.MultiIndex) else []

    for ticker in tickers:
        try:
            sub_df = df.xs(ticker, axis=1, level=1).copy()
            sub_df.columns = [c.lower() for c in sub_df.columns]
            sub_df = sub_df.dropna(subset=['close', 'volume'])

            if len(sub_df) < 5:
                continue

            last_close = sub_df['close'].iloc[-1]
            total_volume_session = sub_df['volume'].sum()
            
            # Estimasi Nilai Transaksi Harian (Total Volume x Harga Terakhir)
            estimated_daily_turnover = total_volume_session * last_close

            # Hitung RSI
            rsi = ta.rsi(sub_df['close'], length=14)
            last_rsi = rsi.iloc[-1] if rsi is not None and not rsi.empty else 50

            stock_info = {
                "ticker": ticker,
                "last_price": last_close,
                "daily_turnover_idr": estimated_daily_turnover,
                "rsi": round(last_rsi, 2)
            }

            # --- LOGIKA KATEGORISASI REVISI ---
            
            # 1. Saham Gorengan / Illiquid / Not Safe:
            # - Harga di bawah Rp 50 (Papan Pemantauan Khusus / Notasi)
            # - Atau total nilai transaksi harian kurang dari Rp 250 Juta
            if estimated_daily_turnover < 250_000_000 or last_close < 50:
                stock_info["category"] = "Gorengan / High Risk"
                stock_info["reason"] = "Likuiditas < Rp 250Juta atau Harga Penny (< Rp 50)"
                gorengan_list.append(stock_info)

            # 2. Safe & Recommended:
            # - Nilai transaksi harian di atas Rp 5 Miliar (Sangat Likuid)
            # - Harga saham >= Rp 200
            elif estimated_daily_turnover >= 5_000_000_000 and last_close >= 200:
                stock_info["category"] = "Safe & Recommended"
                stock_info["reason"] = "Likuiditas Tinggi (>= Rp 5M) & Fundamental Stabil"
                safe_list.append(stock_info)

            # 3. Need Observation:
            # - Saham dengan likuiditas menengah (Rp 250 Juta s/d Rp 5 Miliar)
            # - Berpotensi menjadi setup trading setelah dikonfirmasi indikator lain
            else:
                stock_info["category"] = "Need Observation"
                stock_info["reason"] = "Likuiditas Sedang / Butuh Konfirmasi Indikator Teknikal"
                obs_list.append(stock_info)

        except Exception:
            continue

    # Simpan Hasil Klasifikasi
    now_str = pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M")
    
    pd.DataFrame(safe_list).to_csv(f"../data/categorized/safe/safe_{now_str}.csv", index=False)
    pd.DataFrame(obs_list).to_csv(f"../data/categorized/observation/obs_{now_str}.csv", index=False)
    pd.DataFrame(gorengan_list).to_csv(f"../data/categorized/gorengan/gorengan_{now_str}.csv", index=False)

    print("\n--- HASIL KATEGORISASI DINAMIS PASAR (REVISI) ---")
    print(f"🟢 Safe & Recommended : {len(safe_list)} saham")
    print(f"🟡 Need Observation   : {len(obs_list)} saham")
    print(f"🔴 Saham Gorengan     : {len(gorengan_list)} saham")

if __name__ == "__main__":
    categorize_stocks()
