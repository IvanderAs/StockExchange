import os
import io
import requests
import pandas as pd
import yfinance as yf

os.makedirs("../data/market", exist_ok=True)

def fetch_all_idx_symbols():
    print("🌐 Mengunduh daftar seluruh emiten terdaftar dari Bursa Efek Indonesia (BEI)...")
    tickers = set()

    # Sumber 1: Dataset GitHub IDX Terpercaya & Terupdate
    try:
        url_github = "https://raw.githubusercontent.com/yusuf-adrian/indonesia-stock-exchange-data/main/data/stock_list.json"
        res = requests.get(url_github, timeout=10)
        if res.status_code == 200:
            data = res.json()
            for item in data:
                code = item.get('code') or item.get('symbol') or item.get('ticker')
                if code and len(code) == 4 and code.isalpha():
                    tickers.add(f"{code.upper()}.JK")
            print(f"  [Sumber 1] Berhasil mengambil dari Repositori Data IDX.")
    except Exception as e:
        print(f"  [Sumber 1] Gagal: {e}")

    # Sumber 2: Web Scraping Wikipedia dengan User-Agent Browser Lengkap
    if len(tickers) < 100:
        try:
            url_wiki = "https://id.wikipedia.org/wiki/Daftar_perusahaan_yang_tercatat_di_Bursa_Efek_Indonesia"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(url_wiki, headers=headers, timeout=10)
            tables = pd.read_html(io.StringIO(response.text))
            
            for table in tables:
                for col in table.columns:
                    if any(key in str(col) for key in ['Kode', 'Simbol', 'Ticker']):
                        symbols = table[col].astype(str).str.strip().tolist()
                        for sym in symbols:
                            if len(sym) == 4 and sym.isalpha() and sym.isupper():
                                tickers.add(f"{sym}.JK")
            print(f"  [Sumber 2] Berhasil parse data dari Wikipedia.")
        except Exception as e:
            print(f"  [Sumber 2] Gagal: {e}")

    # Sumber 3: Fallback ke Daftar Emiten BEI Komprehensif (Jika Sumber 1 & 2 Terkendala Koneksi)
    if len(tickers) < 50:
        print("  [Sumber 3] Menggunakan data emiten pasar komprehensif bawaan...")
        known_idx_stocks = [
            "AALI", "ABDA", "ABMM", "ACES", "ACST", "ADES", "ADHI", "ADRO", "AGRO", "AGRS", 
            "AHAP", "AISA", "AKRA", "AKSI", "ALDO", "AMRT", "ANTM", "APEX", "APIC", "APLN", 
            "ARNA", "ARTA", "ASGR", "ASII", "ASRI", "AUTO", "BABP", "BACA", "BAJA", "BBCA", 
            "BBKP", "BBLD", "BBNI", "BBRI", "BBTN", "BBYB", "BCAP", "BCIC", "BDMN", "BEST", 
            "BFIN", "BGTG", "BHIT", "BIMC", "BINA", "BJBR", "BJTM", "BKSL", "BMLA", "BMRI", 
            "BMTR", "BNGA", "BNII", "BNLI", "BSDE", "BSIM", "BTPN", "BUKK", "BUMI", "BYAN", 
            "CASA", "CITA", "CLPI", "CMNP", "CPIN", "CTRA", "DART", "DILD", "DMAS", "DOOID", 
            "DRMA", "ELSA", "EMTK", "ENRG", "ERAA", "EXCL", "FAST", "FPNI", "GDST", "GGRM", 
            "GJTL", "GOTO", "GPRA", "HERO", "HEXA", "HMSP", "IATA", "ICBP", "INCF", "INDF", 
            "INKP", "INTP", "IPTV", "ISAT", "ITMG", "JPFA", "JRPT", "JSMR", "KBLI", "KAEF", 
            "KIJA", "KLBF", "KPIG", "KRAS", "LPCK", "LPKR", "LPPF", "LTLS", "MAPB", "MAPI", 
            "MAYA", "MBSS", "MCOR", "MDKA", "MDLN", "MEDC", "MIKA", "MNCN", "MPPA", "MYOR", 
            "PAAN", "PANR", "PBSD", "PGAS", "PSSI", "PTBA", "PTPP", "PWON", "RALS", "ROTI", 
            "SCMA", "SIDO", "SILO", "SIMP", "SMBR", "SMGR", "SMRA", "SMSM", "SRIL", "SSMS", 
            "TBIG", "TPIA", "TINS", "TLKM", "TOWR", "TRAM", "ULTJ", "UNVR", "WIKA", "WSKT"
        ]
        for s in known_idx_stocks:
            tickers.add(f"{s}.JK")

    final_list = sorted(list(tickers))
    print(f"✅ Ditemukan total {len(final_list)} saham terdaftar di IDX!")
    return final_list

def fetch_full_market_snapshot():
    tickers = fetch_all_idx_symbols()
    if not tickers:
        print("❌ Gagal mendapatkan daftar saham.")
        return None

    print(f"🔍 Mengunduh data snapshot harga pasar untuk {len(tickers)} saham terdaftar...")
    
    # Download data pasar menggunakan multithreading
    data = yf.download(tickers, period="1d", interval="5m", progress=True, threads=True)
    return data

if __name__ == "__main__":
    df_market = fetch_full_market_snapshot()
    if df_market is not None and not df_market.empty:
        now_str = pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M")
        out_file = f"../data/market/full_market_{now_str}.csv"
        df_market.to_csv(out_file)
        print(f"\n✅ Seluruh data pasar IDX tersimpan di {out_file}")
