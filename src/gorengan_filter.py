import os
import glob
import pandas as pd

os.makedirs("data/filtered", exist_ok=True)

def get_latest_technical_file():
    files = glob.glob("data/technical/technical_*.csv")
    if not files:
        return None
    return max(files, key=os.path.getctime)

def filter_saham_gorengan():
    latest_file = get_latest_technical_file()
    if not latest_file:
        print("No technical CSV found in data/technical/")
        return

    print(f"Applying 'Saham Gorengan' & Liquidity Filter on: {latest_file}")
    df = pd.read_csv(latest_file)

    filtered_records = []
    
    # Group by ticker if multi-ticker format
    if 'Ticker' in df.columns:
        tickers = df['Ticker'].unique()
        for ticker in tickers:
            sub_df = df[df['Ticker'] == ticker].copy()
            
            # Skip if missing essential pricing columns
            if 'close' not in sub_df.columns or 'volume' not in sub_df.columns:
                continue
                
            # Drop NaN rows for calculation
            valid_sub = sub_df.dropna(subset=['close', 'volume'])
            if len(valid_sub) < 5:
                continue

            # Calculate average daily volume and recent price volatility
            avg_volume = valid_sub['volume'].mean()
            last_close = valid_sub['close'].iloc[-1]
            estimated_daily_value = avg_volume * last_close # Approximate transaction value in IDR
            
            # --- RISK RULES FOR GORENGAN / ILLIQUID STOCKS ---
            is_gorengan_risk = False
            risk_reason = "Passed"

            # Rule 1: Extremely low liquidity (Average transaction value < Rp 500 Million/day)
            if estimated_daily_value < 500_000_000:
                is_gorengan_risk = True
                risk_reason = "Low Liquidity / High Manipulation Risk"
            
            # Rule 2: Micro-cap penny stock risk (Price below Rp 100/share prone to extreme percentage swings)
            elif last_close < 100:
                is_gorengan_risk = True
                risk_reason = "Penny Stock (< Rp 100) High Volatility"

            sub_df['Is_Safe_To_Trade'] = not is_gorengan_risk
            sub_df['Risk_Flag_Reason'] = risk_reason
            
            filtered_records.append(sub_df)
            print(f" > Ticker {ticker}: Close = Rp {last_close:.2f} | Status: {'SAFE' if not is_gorengan_risk else 'BLOCKED (' + risk_reason + ')'}")
        
        if filtered_records:
            final_filtered_df = pd.concat(filtered_records, axis=0)
        else:
            final_filtered_df = df
    else:
        final_filtered_df = df

    # Save filtered output
    base_name = os.path.basename(latest_file).replace("technical_", "filtered_")
    out_file = f"data/filtered/{base_name}"
    final_filtered_df.to_csv(out_file, index=False)

    print(f"\nSuccess! Filtered dataset saved to {out_file}")

if __name__ == "__main__":
    filter_saham_gorengan()
